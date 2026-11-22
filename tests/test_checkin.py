# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from hlx_api import HlxClient, sign_checkin, md5  # noqa: E402


class TestCheckin(unittest.TestCase):
    def test_sign(self):
        expected = md5(
            "cat_id29time1790000000000"
            "fa1c28a5b62e79c3e63d9030b6142e4b")
        self.assertEqual(sign_checkin(29, "1790000000000"), expected)

    def test_check_in_all(self):
        client = HlxClient()
        client.key = "k"
        urls = []

        def fake(method, url, **kwargs):
            urls.append(url)
            if "/category/list/" in url:
                return {"status": 1, "categories": [
                    {"categoryID": 29, "title": "A"},
                    {"categoryID": 30, "title": "B"},
                ]}
            return {"status": 1, "msg": "签到成功"}

        client._request_json = fake
        with patch("hlx_api.time.sleep", return_value=None):
            ok, total, results = client.check_in_all()
        self.assertEqual((ok, total), (2, 2))
        self.assertTrue(all(item["ok"] for item in results))
        self.assertEqual(len([u for u in urls if "/user/signin/" in u]), 2)


if __name__ == "__main__":
    unittest.main()
