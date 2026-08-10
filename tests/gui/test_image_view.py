from PySide6.QtGui import QPixmap

from kitta.gui.image_view import Background, ImageView, ViewSynchronizer


def make_view(qtbot):
    view = ImageView()
    qtbot.addWidget(view)
    pixmap = QPixmap(100, 100)
    pixmap.fill()
    view.set_pixmap(pixmap)
    view.resize(200, 200)
    view.show()
    return view


def make_synced_views(qtbot, count=3):
    synchronizer = ViewSynchronizer()
    views = [make_view(qtbot) for _ in range(count)]
    for view in views:
        synchronizer.add(view)
    return synchronizer, views


def test_zoom_syncs_all_views(qtbot):
    _, views = make_synced_views(qtbot)

    views[0].zoom(2.0)

    for view in views:
        assert view.transform().m11() == 2.0


def test_zoom_is_clamped(qtbot):
    view = make_view(qtbot)
    view.zoom(1000.0)
    assert view.transform().m11() == 1.0
    view.zoom(0.00001)
    assert view.transform().m11() == 1.0


def test_scroll_syncs_all_views(qtbot):
    _, views = make_synced_views(qtbot)
    views[0].zoom(8.0)
    scrollbar = views[0].horizontalScrollBar()
    assert scrollbar.maximum() > 0

    target = scrollbar.maximum() // 2
    scrollbar.setValue(target)

    for view in views[1:]:
        assert view.horizontalScrollBar().value() == target


def test_sync_does_not_feed_back(qtbot):
    _, views = make_synced_views(qtbot, count=2)
    emissions = []
    views[1].view_changed.connect(lambda: emissions.append(1))

    views[0].zoom(2.0)

    assert emissions == []


def test_fit_all_aligns_views(qtbot):
    synchronizer, views = make_synced_views(qtbot)
    views[0].zoom(4.0)

    synchronizer.fit_all()

    transforms = [view.transform() for view in views]
    assert all(t == transforms[0] for t in transforms)


def test_background_property(qtbot):
    view = make_view(qtbot)
    assert view.background() is Background.CHECKER
    view.set_background(Background.BLACK)
    assert view.background() is Background.BLACK
