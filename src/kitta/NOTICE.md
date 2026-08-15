# Third-Party Notices

Kitta is licensed under the GNU General Public License v3.0 or later
(see LICENSE). It bundles or downloads the following third-party
software and machine-learning models, which remain under their own
licenses.

## Bundled Python packages

| Package | License |
| --- | --- |
| PySide6 / Shiboken6 (Qt for Python) | LGPL-3.0-only |
| rembg | MIT |
| onnxruntime | MIT |
| Pillow | MIT-CMU |
| NumPy | BSD-3-Clause |
| SciPy | BSD-3-Clause |
| opencv-python-headless (OpenCV) | Apache-2.0 |
| scikit-image | BSD-3-Clause |
| pooch | BSD-3-Clause |
| tqdm | MPL-2.0 AND MIT |
| PyMatting | MIT |
| Numba | BSD-2-Clause |
| llvmlite | BSD-2-Clause AND Apache-2.0 WITH LLVM-exception |
| requests | Apache-2.0 |
| tomli-w | MIT |

PySide6 and Shiboken6 are dynamically linked and used under the terms of
the GNU Lesser General Public License v3.0. Their complete corresponding
source code is available at
<https://code.qt.io/cgit/pyside/pyside-setup.git/>.

## Machine-learning models (downloaded on demand)

| Model | Preset | License | Source |
| --- | --- | --- | --- |
| U²-Net (u2netp) | Fast | Apache-2.0 | <https://github.com/xuebinqin/U-2-Net> |
| U²-Net (u2net) | — | Apache-2.0 | <https://github.com/xuebinqin/U-2-Net> |
| U²-Net Human (u2net_human_seg) | — | Apache-2.0 | <https://github.com/xuebinqin/U-2-Net> |
| U²-Net Cloth (u2net_cloth_seg) | — | MIT | <https://github.com/levindabhi/cloth-segmentation> |
| Silueta | — | Apache-2.0 | <https://github.com/xuebinqin/U-2-Net> |
| ISNet General (DIS) | Balanced | Apache-2.0 | <https://github.com/xuebinqin/DIS> |
| ISNet Anime | Anime | Apache-2.0 | <https://github.com/SkyTNT/anime-segmentation> |
| BiRefNet General | High Quality | MIT | <https://github.com/ZhengPeng7/BiRefNet> |
| BiRefNet Lite | — | MIT | <https://github.com/ZhengPeng7/BiRefNet> |
| BiRefNet Portrait | Portrait | MIT | <https://github.com/ZhengPeng7/BiRefNet> |
| BiRefNet DIS | — | MIT | <https://github.com/ZhengPeng7/BiRefNet> |
| BiRefNet HRSOD | — | MIT | <https://github.com/ZhengPeng7/BiRefNet> |
| BiRefNet COD | — | MIT | <https://github.com/ZhengPeng7/BiRefNet> |
| BiRefNet Massive | — | MIT | <https://github.com/ZhengPeng7/BiRefNet> |
| BRIA RMBG 2.0 | — | BRIA RMBG-2.0 (non-commercial) | <https://huggingface.co/briaai/RMBG-2.0> |

Model files are downloaded on demand from the rembg project's release
storage (<https://github.com/danielgatis/rembg>). Models are not part of
the Kitta distribution itself and are cached locally on your machine.
