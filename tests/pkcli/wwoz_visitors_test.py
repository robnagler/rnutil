"""test wwoz visitors pkcli

:copyright: Copyright (c) 2026 Robert Nagler.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_visitors():
    from pykern import pkunit
    from rnutil.pkcli import wwoz

    for case in pkunit.case_dirs():
        case.join("table.txt").write(wwoz.visitors(html_dir=case))
