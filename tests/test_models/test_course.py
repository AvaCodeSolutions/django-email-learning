def test_enrollments_count_property(course, enrollments_factory):
    enrollments_factory(course=course, status="unverified", count=3)
    enrollments_factory(course=course, status="active", count=5)
    enrollments_factory(course=course, status="completed", count=2)
    enrollments_factory(course=course, status="deactivated", count=1)

    counts = course.enrollments_count
    assert counts["unverified"] == 3
    assert counts["active"] == 5
    assert counts["completed"] == 2
    assert counts["deactivated"] == 1
    assert counts["total"] == 11
