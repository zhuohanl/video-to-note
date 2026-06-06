from importlib import import_module

PACKAGES = [
    "vtn_core",
    "vtn_ingest",
    "vtn_transcript",
    "vtn_visual",
    "vtn_style",
    "vtn_segment",
    "vtn_notes",
    "vtn_export",
    "vtn_storage",
    "vtn_ai",
]


def test_workspace_packages_import_and_identify_themselves() -> None:
    for package_name in PACKAGES:
        package = import_module(package_name)
        assert package.hello() == package_name


def test_style_dependency_direction_is_one_way() -> None:
    segment = import_module("vtn_segment")
    style = import_module("vtn_style")

    assert segment.style_package_name() == "vtn_style"
    assert not hasattr(style, "segment_package_name")
