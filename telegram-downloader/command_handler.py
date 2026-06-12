
import os
from pyrogram import Client, filters, __version__ as pyrogram_version
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import enums

from env import Env
from command_controller import CommandController
from command_help import CommandHelp
from data_handler import FileDataHandler
from logger_config import logger

class CommandHandler:
    def __init__(self, config):
        self.env = Env()
        self.command_controller = CommandController()

        self.command_dict = {
            "ehelp": self.ehandle_help,
            "start": self.handle_start,
            "help": self.handle_help,
            "stats": self.handle_stats,
            "pyrogram": self.handle_pyrogram_version,
            "ytdlp": self.handle_ytdlp_version,
            "version": self.handle_version,
            "id": self.handle_id,
            "rename": self.rename_file,
            "move": self.rename_file,
            "addextensionpath": self.addExtensionPath,
            "delextensionpath": self.delExtensionPath,
            "addgrouppath": self.addGroupPath,
            "delgrouppath": self.delGroupPath,
            "addkeywordpath": self.addKeywordPath,
            "delkeywordpath": self.delKeywordPath,
            "addrenamegroup": self.addRenameGroup,
            "delrenamegroup": self.addRenameGroup,
            "broadcast": self.handle_broadcast,
        }

        self.command_keys = list(self.command_dict.keys())
        self.bot_version = config.BOT_VERSION
        self.yt_dlp_version = config.YT_DLP_VERSION
        self.pyrogram_version = pyrogram_version


    async def process_command(self, client: Client, message: Message):
        try:

            command = message.command[0]

            user_id = message.from_user.id if message.from_user else None
            if not str(user_id) in self.env.AUTHORIZED_USER_ID and command not in ('id', 'start'):
                return False

            logger.info(f"process_command:: {command}")
            handler_method = self.command_dict.get(command)

            if self._function_accepts_args(handler_method):
                return await handler_method(client, message)
            else:
                return await handler_method()

        except Exception as e:
            logger.error(f"process_command => Exception: {e}")

    def _function_accepts_args(self, func):
        # Verificar si la función acepta argumentos adicionales
        return hasattr(func, "__code__") and func.__code__.co_argcount > 1

    async def ehandle_help(self, client: Client, message: Message):

        help_text = CommandHelp.get_ehelp()
        
        while help_text:
            # Toma un fragmento de texto de hasta 4096 caracteres.
            chunk = help_text[:4096]
            if len(help_text) > 4096:
                # Encuentra el último espacio para no cortar palabras.
                split_index = chunk.rfind(" ")
                if split_index == -1:  # Si no hay espacios, corta en el límite.
                    split_index = 4096
                chunk = help_text[:split_index]
                help_text = help_text[split_index:].strip()
            else:
                help_text = ""  # Última parte.

            # Envía el fragmento.
            await client.send_message(message.chat.id, chunk)
        
        #await message.reply_text(help_text, parse_mode=enums.ParseMode.DISABLED)

    async def handle_start(self, client: Client, message: Message):
        first_name = message.from_user.first_name if message.from_user and message.from_user.first_name else "صديقي"
        caption = (
            f"أهلاً بك يا {first_name} في بوت التحميل! 🚀\n\n"
            "يمكنك استخدام البوت لتحميل الملفات والوسائط بسهولة.\n\n"
            "اختر أحد الخيارات أدناه:"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("قناة الدعم ⚙️", url="https://t.me/shaheen_ys"),
                InlineKeyboardButton("هدية يومية 🎁", url="https://t.me/shaheen_mall_ys"),
            ],
            [
                InlineKeyboardButton("📊 الإحصائيات", callback_data="cmd_stats"),
                InlineKeyboardButton("❓ المساعدة", callback_data="cmd_help"),
            ],
            [
                InlineKeyboardButton("ℹ️ الإصدار", callback_data="cmd_version"),
                InlineKeyboardButton("🆔 معرّفي", callback_data="cmd_id"),
            ],
            [
                InlineKeyboardButton("👨‍💻 المطور", callback_data="developer_card"),
            ],
        ])
        try:
            await client.send_video(
                chat_id=message.chat.id,
                video="https://files.catbox.moe/ek7mkp.mp4",
                caption=caption,
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.error(f"handle_start send_video error: {e}")
            await message.reply_text(caption, reply_markup=keyboard)

    async def handle_stats(self, client: Client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        if not str(user_id) in self.env.AUTHORIZED_USER_ID:
            await message.reply_text("⛔ هذا الأمر متاح للمسؤول فقط.")
            return
        await _send_stats(client, message.chat.id)

    async def handle_broadcast(self, client: Client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        if not str(user_id) in self.env.AUTHORIZED_USER_ID:
            await message.reply_text("⛔ هذا الأمر متاح للمسؤول فقط.")
            return

        # Determine what to broadcast
        broadcast_text = None
        reply_msg = message.reply_to_message

        args = message.command[1:]
        if args:
            broadcast_text = " ".join(args)

        if not broadcast_text and not reply_msg:
            await message.reply_text(
                "📢 **طريقة الاستخدام:**\n\n"
                "• `/broadcast <نص الرسالة>` — بث نص مباشر\n"
                "• قم بالرد على رسالة واكتب `/broadcast` — لإعادة إرسال تلك الرسالة"
            )
            return

        # Collect unique user IDs from the download DB
        db = FileDataHandler()
        unique_ids = list({r["user_id"] for r in db.downloads if r.get("user_id")})

        if not unique_ids:
            await message.reply_text("⚠️ لا يوجد مستخدمون في قاعدة البيانات بعد.")
            return

        status_msg = await message.reply_text(
            f"📤 جارٍ الإرسال إلى {len(unique_ids)} مستخدم..."
        )

        sent = 0
        failed = 0
        blocked = 0

        for uid in unique_ids:
            try:
                if reply_msg:
                    await reply_msg.forward(uid)
                else:
                    await client.send_message(uid, broadcast_text)
                sent += 1
            except Exception as e:
                err = str(e).lower()
                if "blocked" in err or "user is deactivated" in err or "forbidden" in err:
                    blocked += 1
                else:
                    failed += 1
                logger.warning(f"broadcast to {uid} failed: {e}")

        await status_msg.edit_text(
            f"✅ **اكتمل البث**\n\n"
            f"📨 أُرسل بنجاح: **{sent}**\n"
            f"🚫 محظور / غير نشط: **{blocked}**\n"
            f"❌ فشل: **{failed}**\n"
            f"👥 الإجمالي: **{len(unique_ids)}**"
        )

    async def handle_help(self, client: Client, message: Message):


        help_text = CommandHelp.get_help()

        await message.reply_text(help_text, parse_mode=enums.ParseMode.DISABLED)

    async def handle_id(self, client: Client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        await message.reply_text(f"id: {str(user_id)}")

    async def handle_version(self, client: Client, message: Message):
        await message.reply_text(f"version: {str(self.bot_version)}")

    async def handle_pyrogram_version(self, client: Client, message: Message):
        await message.reply_text(f"pyrogram version: {self.pyrogram_version}")

    async def handle_ytdlp_version(self, client: Client, message: Message):
        await message.reply_text(f"ytdlp version: {self.yt_dlp_version}")

    ########## ------------------------------------------------------------------------------------


    def getTempFilename(self, client: Client, message: Message):
        return self.command_controller.getTempFilename(client, message)
    
    async def rename_file(self, client: Client, message: Message):
        await self.command_controller.renameFiles(client, message)

    async def addExtensionPath(self, client: Client, message: Message):
        await self.command_controller.addExtensionPath(client, message)

    async def delExtensionPath(self, client: Client, message: Message):
        await self.command_controller.delExtensionPath(client, message)

    async def addGroupPath(self, client: Client, message: Message):
        await self.command_controller.addGroupPath(client, message)

    async def delGroupPath(self, client: Client, message: Message):
        await self.command_controller.delGroupPath(client, message)

    async def addKeywordPath(self, client: Client, message: Message):
        await self.command_controller.addKeywordPath(client, message)

    async def delKeywordPath(self, client: Client, message: Message):
        await self.command_controller.delKeywordPath(client, message)

    async def addRenameGroup(self, client: Client, message: Message):
        await self.command_controller.addRenameGroup(client, message)

    async def delRenameGroup(self, client: Client, message: Message):
        await self.command_controller.delRenameGroup(client, message)

