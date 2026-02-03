"""Help plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v1

from . import BASE_URL


class HelpPlugin(WebserverPlugin):
    """Help plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}help/getHelpIndex", _handle_get_help_index),
            web.route("*", f"{BASE_URL}help/getProductHelpIndex", _handle_get_product_help_index),
        ]


async def _handle_get_help_index(_: Request) -> Response:
    """Get help index."""
    return response_success_v1(
        {
            "indexProductList": [
                {
                    "imgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5cf711aeb0acfc000179ff8a",
                    "isConfNet": "Y",
                    "marketName": "DEEBOT OZMO/PRO 930 Series",
                    "materialNo": "110-1602-0101",
                    "model": "DR930",
                    "productId": "20200115064102_59428181dfdcae88ea5b745415e30d37",
                },
                {
                    "imgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/606278df4a84d700082b39f1",
                    "isConfNet": "Y",
                    "marketName": "DEEBOT OZMO 950 Series",
                    "materialNo": "110-1820-0101",
                    "model": "DX9G",
                    "productId": "20200115064101_c871daa7c1cb74f447d4fcdb38040eaf",
                },
                {
                    "imgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/61f0ba7970c881c6bf65ec3d",
                    "isConfNet": "Y",
                    "marketName": "DEEBOT T10 PLUS",
                    "materialNo": "110-2113-0301",
                    "model": "CURIE_AES_INT_OK",
                    "productId": "20220127010107_783c591a6632cc89c914cc0d8f2d338e",
                },
                {
                    "imgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/624d4e73031bdd7c7b531af9",
                    "isConfNet": "N",
                    "marketName": "AIRBOT Z1",
                    "materialNo": "113-2109-0200",
                    "model": "BRUCE_INT",
                    "productId": "20220407010045_bd1a7f60c8befe4c79c4e8b8e6f35c76",
                },
                {
                    "imgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5c874326280fda0001770d2a",
                    "isConfNet": "N",
                    "marketName": "DEEBOT 500",
                    "materialNo": "702-0000-0163",
                    "model": "D500",
                    "productId": "20200115064057_5aa61e982672ae0c5a1883e3260eb869",
                },
                {
                    "imgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5c931fef280fda0001770d7e",
                    "isConfNet": "N",
                    "marketName": "DEEBOT 501",
                    "materialNo": "702-0000-0169",
                    "model": "D501",
                    "productId": "20200115064057_db0462273510a60eaaae32a78923491f",
                },
                {
                    "imgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5c93204b63023c0001e7faa7",
                    "isConfNet": "N",
                    "marketName": "DEEBOT 502",
                    "materialNo": "702-0000-0161",
                    "model": "D502",
                    "productId": "20200115064057_7a8ea52adf4b96a8b9752315ae86c8b5",
                },
                {
                    "imgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5c932067280fda0001770d7f",
                    "isConfNet": "N",
                    "marketName": "DEEBOT 505",
                    "materialNo": "20200115005",
                    "model": "D505",
                    "productId": "20200115064057_024db39cda0d9f092563c364f62c5b50",
                },
            ],
            "moreHelpModuleList": [],
        },
    )


async def _handle_get_product_help_index(_: Request) -> Response:
    """Get product help index."""
    url_01 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20230428010042_1bc8d9bd2ee5a7e7b7956654db4062b0&lang=EN"
    url_02 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_cd763556564ff0a61fc41d2624908891&lang=EN"
    url_03 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_3657ef5c16da7cbcaab698b21fb2ecc0&lang=EN"
    url_04 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_0e70117dde190eb6dce3b6244e79d517&lang=EN"
    url_05 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_cb47cb63c80300bef9cc3db74950fcd7&lang=EN"
    url_06 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_8aabbbfc0d85e9d1a031a1417ff27fb8&lang=EN"
    url_07 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200115064101_4bbc5047c0f483044342546bc7b63df2&lang=EN"
    url_08 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200115064101_6cc9eae8d3e4d8cd5a9429e43a1e2474&lang=EN"
    url_09 = f"https://{bumper_isc.DOMAIN_ALI}/Universal%20video/How%20to%20connect%20ECOVACS%20Home%20App-for%20Android.mp4"
    url_10 = f"https://{bumper_isc.DOMAIN_ALI}/Universal%20video/How%20to%20connect%20ECOVACS%20Home%20App-for%20Android.mp4"
    url_11 = f"https://{bumper_isc.DOMAIN_ALI}/Universal%20video/How%20to%20connect%20ECOVACS%20Home%20App-for%20iOS.mp4"
    url_12 = f"https://{bumper_isc.DOMAIN_ALI}/Universal%20video/How%20to%20pair%20smart%20home%20device-Amazon%20Echo.mp4"
    url_13 = f"https://{bumper_isc.DOMAIN_ALI}/Universal%20video/How%20to%20pair%20smart%20home%20device-Google%20Home.mp4"
    url_14 = f"https://{bumper_isc.DOMAIN_ALI}/Universal%20video/How%20to%20start%20using%20your%20Ecovacs%20robot.mp4"
    url_15 = f"https://{bumper_isc.DOMAIN_ALI}/Universal%20video/Learn%20more%20features%20with%20ECOVACS%20Home%20App.mp4"
    url_16 = f"https://{bumper_isc.DOMAIN_ALI}/Universal%20video/How%20to%20use%20Smart%20Navi3.0.mp4"
    view_url = (
        f"https://{bumper_isc.DOMAIN_SEC3}"
        "/product/instructions?instructionsId=20200115064102_39366488ec99d1980b7da5ae5e414994&lang=EN"
    )
    title_07 = (
        "I forgot my Ecovacs account number and password,"
        " but when I click “Forgot password” I don't receive an authentication email. What should I do?"
    )

    return response_success_v1(
        {
            "faqResponse": {
                "faqList": [
                    {
                        "faqId": "20230428010042_1bc8d9bd2ee5a7e7b7956654db4062b0",
                        "title": "How to disassemble the mopping plate?",
                        "url": url_01,
                    },
                    {
                        "faqId": "20200324010022_cd763556564ff0a61fc41d2624908891",
                        "title": "Making your first map with your OZMO 920 / 950",
                        "url": url_02,
                    },
                    {
                        "faqId": "20200324010022_3657ef5c16da7cbcaab698b21fb2ecc0",
                        "title": "Continuous Cleaning Feature on your OZMO 920 / 950",
                        "url": url_03,
                    },
                    {
                        "faqId": "20200324010022_0e70117dde190eb6dce3b6244e79d517",
                        "title": "Virtual Boundaries with your OZMO 920 / 950",
                        "url": url_04,
                    },
                    {
                        "faqId": "20200324010022_cb47cb63c80300bef9cc3db74950fcd7",
                        "title": "Losing and Recovering Maps",
                        "url": url_05,
                    },
                    {
                        "faqId": "20200324010022_8aabbbfc0d85e9d1a031a1417ff27fb8",
                        "title": "What's the difference between the OZMO 920 and the OZMO 950?",
                        "url": url_06,
                    },
                    {
                        "faqId": "20200115064101_4bbc5047c0f483044342546bc7b63df2",
                        "title": title_07,
                        "url": url_07,
                    },
                    {
                        "faqId": "20200115064101_6cc9eae8d3e4d8cd5a9429e43a1e2474",
                        "title": "DEEBOT is cleaning with a louder noise than normal. What should I do?",
                        "url": url_08,
                    },
                ],
                "hasMore": "Y",
            },
            "headImgResponse": {"clickAction": "", "clickURL": None, "headImgUrl": None, "params": {}},
            "instructions": {
                "downloadUrl": f"https://{bumper_isc.DOMAIN_ALI}/OZMO950/DX9GDEESFRITRU.pdf",
                "viewUrl": view_url,
            },
            "productResponse": {
                "imgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/606278df4a84d700082b39f1",
                "marketName": "DEEBOT OZMO 950 Series",
                "materialNo": "110-1820-0101",
                "model": "DX9G",
                "productId": "20200115064101_c871daa7c1cb74f447d4fcdb38040eaf",
            },
            "skillsResponse": None,
            "videoList": [
                {
                    "coverImgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5e1d1b9bf024120001a329a1",
                    "url": url_09,
                    "videoId": "20200115064102_53712c13629a24d93f1dfeeb414dbe0e",
                },
                {
                    "coverImgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5e1d1b9d1ec5e60001e80ede",
                    "url": url_10,
                    "videoId": "20200115064102_d8c1d0a45ee63a9d4e4220cc78c00f67",
                },
                {
                    "coverImgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5e1d1ca01ec5e60001e80edf",
                    "url": url_11,
                    "videoId": "20200115064102_a8ea7077bd83ba24d15b65471adbbad7",
                },
                {
                    "coverImgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5e1d1ce81ec5e60001e80ee4",
                    "url": url_12,
                    "videoId": "20200115064102_224e23c73bc9d351036cebe732e9a169",
                },
                {
                    "coverImgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5e1d1d0b1ec5e60001e80ee5",
                    "url": url_13,
                    "videoId": "20200115064102_eedca6a77557529138b667912ced1281",
                },
                {
                    "coverImgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5e1d1d631ec5e60001e80ee9",
                    "url": url_14,
                    "videoId": "20200115064102_9d6cbb0901c268c3df8ab60f95fe56d7",
                },
                {
                    "coverImgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5e1d1d901ec5e60001e80eec",
                    "url": url_15,
                    "videoId": "20200115064102_d794f817dc24ae9b379c7edfa0bb7c4e",
                },
                {
                    "coverImgUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/api/pim/file/get/5e1d1dc11ec5e60001e80ef1",
                    "url": url_16,
                    "videoId": "20200115064102_160366390cc2205aeb20515674ddd4ec",
                },
            ],
        },
    )
