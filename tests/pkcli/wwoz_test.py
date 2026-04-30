"""test wwoz pkcli

:copyright: Copyright (c) 2026 Robert Nagler.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_livewire():
    from pykern import pkunit, pkjson
    from rnutil.pkcli import wwoz

    for case in pkunit.case_dirs():
        html = case.join("livewire.html").read()
        events = wwoz._parse(html)
        case.join("livewire.json").write(wwoz._Output(False, events).as_str())
        case.join("table.txt").write(wwoz._Output(True, events).as_str())
