from app.grouping import build_groups, related_reports, tokenize


def R(i, b="block_b", c="broken_stairs", d="cracked step at entrance", loc="", s="open", t="2026-01-01T00:00:00"):
    return dict(id=i, building=b, category=c, description=d, location_details=loc, status=s, created_at=t)


def test_links_same_building_and_category_only():
    reps = [R(1), R(2), R(3, b="library"), R(4, c="pothole")]
    assert [x["id"] for x in related_reports(reps[0], reps)] == [2]


def test_never_links_self():
    assert related_reports(R(1), [R(1)]) == []


def test_similarity_is_evidence_not_a_requirement():
    a, b = R(1, d="cracked step entrance"), R(2, d="completely different words here")
    rel = related_reports(a, [a, b])
    assert len(rel) == 1 and rel[0]["description_similarity"] == 0.0


def test_description_similarity_and_location_overlap():
    a = R(1, d="Loose cracked step at the entrance", loc="left side stairs")
    b = R(2, d="cracked loose step entrance", loc="Stairs left")
    rel = related_reports(a, [a, b])[0]
    assert rel["description_similarity"] > 0.5 and rel["location_details_overlap"]


def test_build_groups_counts_open():
    reps = [R(1), R(2, s="resolved"), R(3, b="library")]
    g = build_groups(reps)
    assert len(g) == 1 and g[0]["size"] == 2 and g[0]["open_count"] == 1


def test_tokenize_drops_stopwords():
    assert "the" not in tokenize("the broken stairs")
