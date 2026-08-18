from api.release import release_git_sha


def test_platform_deploy_sha_wins_over_stale_caregist_pin():
    sha = release_git_sha(
        {
            "CAREGIST_RELEASE_SHA": "f" * 40,
            "VERCEL_GIT_COMMIT_SHA": "a" * 40,
        }
    )
    assert sha == "a" * 40


def test_caregist_pin_used_when_no_platform_sha():
    assert release_git_sha({"CAREGIST_RELEASE_SHA": "B" * 40}) == "b" * 40


def test_invalid_sha_is_unknown():
    assert release_git_sha({"VERCEL_GIT_COMMIT_SHA": "not-a-sha"}) == "unknown"
