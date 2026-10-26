from datetime import date

from tools.find_cqc_ratings_file import edition_from_name, newest, ratings_links

PAGE = "https://www.cqc.org.uk/about-us/transparency/using-cqc-data"


def test_edition_date_is_read_from_either_filename_style():
    assert edition_from_name("/sites/default/files/2026-08-04_Latest_ratings.ods") == date(2026, 8, 4)
    assert edition_from_name("01_October_2026_Latest_ratings.ods") == date(2026, 10, 1)
    assert edition_from_name("01%20October%202026%20Latest%20ratings.ods") == date(2026, 10, 1)
    assert edition_from_name("ratings.ods") is None


def test_newest_dated_ratings_file_wins_and_undated_is_never_guessed():
    html = (
        '<a href="/sites/default/files/2026-09-01_Latest_ratings.ods">Sept</a>'
        '<a href="/sites/default/files/2026-10-02_Latest_ratings.ods">Oct</a>'
        '<a href="/sites/default/files/ratings.ods">undated</a>'
        '<a href="/sites/default/files/2026-10-14_CQC_directory.ods">not ratings</a>'
    )
    links = ratings_links(html, PAGE)
    assert len(links) == 3
    url, edition = newest(links)
    assert url == "https://www.cqc.org.uk/sites/default/files/2026-10-02_Latest_ratings.ods"
    assert edition == date(2026, 10, 2)
    assert newest(["https://x/ratings.ods"]) is None
