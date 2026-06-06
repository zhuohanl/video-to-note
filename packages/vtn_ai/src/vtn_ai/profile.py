from vtn_ai.fake import FakeProfile, build_fake_profile


def get_profile(name: str) -> FakeProfile:
    if name == "fake":
        return build_fake_profile()

    msg = f"unknown profile: {name}"
    raise ValueError(msg)
