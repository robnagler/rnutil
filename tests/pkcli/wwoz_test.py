"""test wwoz pkcli

:copyright: Copyright (c) 2026 Robert Nagler.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_parse():
    from pykern import pkunit, pkjson
    from rnutil.pkcli import wwoz

    html = pkunit.data_dir().join("livewire.html").read()
    result = wwoz.parse(html)
    pkunit.pkeq(pkjson.load_any(pkunit.data_dir().join("livewire.json")), result)
