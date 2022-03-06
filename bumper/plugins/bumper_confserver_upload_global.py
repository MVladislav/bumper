import logging
import os

from aiohttp import web

from bumper import bumper_dir, plugins


class upload_global(plugins.ConfServerApp):
    def __init__(self):
        self.name = "upload_global"
        self.plugin_type = "sub_api"
        self.sub_api = "upload_api"

        self.routes = [
            web.route(
                "*",
                "/global/{year}/{month}/{day}/{fileid}",
                self.handle_upload_global_file,
                name="upload_global_getFile",
            ),
        ]

    async def handle_upload_global_file(self, request):
        try:
            fileID = request.match_info.get("id", "")

            return web.FileResponse(
                os.path.join(
                    bumper_dir, "bumper", "web", "images", "robotvac_image.jpg"
                )
            )

        except Exception as e:
            logging.exception(f"{e}")
