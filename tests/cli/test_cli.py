import pytest
from PIL import Image

from kitta.cli.main import main
from kitta.core import compare as compare_mod
from kitta.core import model_store
from kitta.core import remove as remove_mod
from kitta.core.remove import RemovalResult


def fake_result(preset) -> RemovalResult:
    rgba = Image.new("RGBA", (8, 8), (255, 0, 0, 128))
    return RemovalResult(
        image=rgba,
        mask=rgba.getchannel("A"),
        elapsed=0.01,
        model_name=preset.model.name,
        preset_name=preset.name,
    )


@pytest.fixture
def fake_inference(monkeypatch):
    """Replace model download and inference with instant fakes."""
    monkeypatch.setattr(model_store, "is_available", lambda spec, models_dir=None: True)
    monkeypatch.setattr(remove_mod, "remove_background", lambda image, preset: fake_result(preset))
    monkeypatch.setattr(compare_mod, "remove_background", lambda image, preset: fake_result(preset))


@pytest.fixture
def input_image(tmp_path, sample_image):
    path = tmp_path / "photo.jpg"
    sample_image.save(path)
    return path


def test_single_image_default_output(fake_inference, input_image, capsys):
    assert main([str(input_image)]) == 0
    output = input_image.with_name("photo-cutout.png")
    assert output.exists()
    assert Image.open(output).mode == "RGBA"
    assert "photo-cutout.png" in capsys.readouterr().out


def test_single_image_explicit_output_and_mask(fake_inference, input_image, tmp_path):
    output = tmp_path / "out" / "result.png"
    output.parent.mkdir()
    assert main([str(input_image), "-o", str(output), "--mask"]) == 0
    assert output.exists()
    mask = output.parent / "photo-mask.png"
    assert mask.exists()
    assert Image.open(mask).mode == "L"


def test_single_image_with_model(fake_inference, input_image, capsys):
    assert main([str(input_image), "--model", "u2netp"]) == 0
    assert "u2netp" in capsys.readouterr().out


def test_single_image_with_preset_file(fake_inference, input_image, tmp_path):
    preset_file = tmp_path / "custom.toml"
    preset_file.write_text('model = "u2netp"\n', encoding="utf-8")
    assert main([str(input_image), "--preset", str(preset_file)]) == 0


def test_model_and_preset_conflict(input_image):
    with pytest.raises(SystemExit) as excinfo:
        main([str(input_image), "--model", "u2netp", "--preset", "fast"])
    assert excinfo.value.code == 2


def test_unknown_preset(input_image, capsys):
    assert main([str(input_image), "--preset", "nope"]) == 1
    assert "unknown preset" in capsys.readouterr().err


def test_missing_input_file(fake_inference, tmp_path, capsys):
    assert main([str(tmp_path / "none.jpg")]) == 1
    assert "file not found" in capsys.readouterr().err


def test_compare_with_presets(fake_inference, input_image, tmp_path, capsys):
    outdir = tmp_path / "results"
    code = main(
        [
            "compare",
            str(input_image),
            "--presets",
            "fast,balanced",
            "--output-dir",
            str(outdir),
        ]
    )
    assert code == 0
    assert (outdir / "photo-fast.png").exists()
    assert (outdir / "photo-balanced.png").exists()
    out = capsys.readouterr().out
    assert "2/2 succeeded" in out


def test_compare_with_models(fake_inference, input_image, capsys):
    assert main(["compare", str(input_image), "--models", "u2netp"]) == 0
    assert input_image.with_name("photo-u2netp.png").exists()


def test_compare_reports_failure(monkeypatch, fake_inference, input_image, capsys):
    def flaky(image, preset):
        if preset.name == "fast":
            raise RuntimeError("boom")
        return fake_result(preset)

    monkeypatch.setattr(compare_mod, "remove_background", flaky)
    code = main(["compare", str(input_image), "--presets", "fast,balanced"])
    assert code == 1
    captured = capsys.readouterr()
    assert "1/2 succeeded" in captured.out
    assert "boom" in captured.err


def test_batch(fake_inference, tmp_path, sample_image, capsys):
    indir = tmp_path / "in"
    indir.mkdir()
    for name in ("a.jpg", "b.png", "c.webp"):
        sample_image.save(indir / name)
    (indir / "notes.txt").write_text("not an image")
    outdir = tmp_path / "out"

    code = main(["batch", str(indir), "--preset", "fast", "--output", str(outdir)])

    assert code == 0
    assert sorted(p.name for p in outdir.iterdir()) == ["a.png", "b.png", "c.png"]
    assert "processed 3, skipped 0, failed 0 (of 3)" in capsys.readouterr().out


def test_batch_skip_existing(fake_inference, tmp_path, sample_image, capsys):
    indir = tmp_path / "in"
    indir.mkdir()
    sample_image.save(indir / "a.jpg")
    outdir = tmp_path / "out"
    outdir.mkdir()
    (outdir / "a.png").write_bytes(b"existing")

    code = main(
        ["batch", str(indir), "--preset", "fast", "--output", str(outdir), "--skip-existing"]
    )

    assert code == 0
    assert (outdir / "a.png").read_bytes() == b"existing"
    assert "processed 0, skipped 1, failed 0 (of 1)" in capsys.readouterr().out


def test_batch_continues_after_error(monkeypatch, fake_inference, tmp_path, sample_image, capsys):
    indir = tmp_path / "in"
    indir.mkdir()
    sample_image.save(indir / "a.jpg")
    sample_image.save(indir / "b.jpg")
    (indir / "broken.jpg").write_bytes(b"not really an image")
    outdir = tmp_path / "out"

    code = main(["batch", str(indir), "--preset", "fast", "--output", str(outdir)])

    assert code == 1
    assert (outdir / "a.png").exists()
    assert (outdir / "b.png").exists()
    captured = capsys.readouterr()
    assert "processed 2, skipped 0, failed 1 (of 3)" in captured.out
    assert "broken.jpg" in captured.err


def test_batch_empty_dir(fake_inference, tmp_path, capsys):
    indir = tmp_path / "empty"
    indir.mkdir()
    code = main(["batch", str(indir), "--preset", "fast", "--output", str(tmp_path / "out")])
    assert code == 1
    assert "no image files" in capsys.readouterr().err


def test_licenses_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--licenses"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "PySide6" in out
    assert "BiRefNet" in out


def test_keyboard_interrupt(monkeypatch, fake_inference, input_image, capsys):
    def interrupted(image, preset):
        raise KeyboardInterrupt

    monkeypatch.setattr(remove_mod, "remove_background", interrupted)

    assert main([str(input_image)]) == 130
    assert "interrupted" in capsys.readouterr().err


@pytest.mark.inference
def test_single_image_real_u2netp(input_image, tmp_path):
    output = tmp_path / "real.png"
    assert main([str(input_image), "--preset", "fast", "-o", str(output)]) == 0
    assert Image.open(output).mode == "RGBA"
