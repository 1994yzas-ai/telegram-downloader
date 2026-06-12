
import os
from pyrogram import Client, filters, __version__ as pyrogram_version
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import enums

from env import Env
from command_controller import CommandController
from command_help import CommandHelp
from data_handler import FileDataHandler
from ban_handler import BanHandler
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
            "users": self.handle_users,
            "ban": self.handle_ban,
            "unban": self.handle_unban,
            "banned": self.handle_banned_list,
            "delete": self.handle_delete,
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

    async def handle_ban(self, client: Client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        if not str(user_id) in self.env.AUTHORIZED_USER_ID:
            await message.reply_text("⛔ هذا الأمر متاح للمسؤول فقط.")
            return

        target_id = None
        reason = ""

        # Priority: reply to a message → extract sender; else parse argument
        if message.reply_to_message and message.reply_to_message.from_user:
            target_id = message.reply_to_message.from_user.id
            args = message.command[1:]
            reason = " ".join(args)
        elif len(message.command) > 1:
            try:
                target_id = int(message.command[1])
                reason = " ".join(message.command[2:])
            except ValueError:
                await message.reply_text("⚠️ يرجى تحديد معرّف رقمي صحيح.\n مثال: `/ban 123456789 سبب الحظر`")
                return
        else:
            await message.reply_text(
                "📢 **طريقة الاستخدام:**\n\n"
                "• رد على رسالة المستخدم واكتب `/ban <السبب>`\n"
                "• أو: `/ban <معرّف المستخدم> <السبب>`"
            )
            return

        if str(target_id) in self.env.AUTHORIZED_USER_ID:
            await message.reply_text("⛔ لا يمكنك حظر المسؤول.")
            return

        bh = BanHandler()
        if bh.ban(target_id, reason):
            reason_line = f"\n📝 **السبب:** {reason}" if reason else ""
            await message.reply_text(f"🚫 تم حظر المستخدم `{target_id}` بنجاح.{reason_line}")
            logger.info(f"User {target_id} banned by {user_id}. Reason: {reason}")
        else:
            await message.reply_text(f"⚠️ المستخدم `{target_id}` محظور مسبقاً.")

    async def handle_unban(self, client: Client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        if not str(user_id) in self.env.AUTHORIZED_USER_ID:
            await message.reply_text("⛔ هذا الأمر متاح للمسؤول فقط.")
            return

        target_id = None

        if message.reply_to_message and message.reply_to_message.from_user:
            target_id = message.reply_to_message.from_user.id
        elif len(message.command) > 1:
            try:
                target_id = int(message.command[1])
            except ValueError:
                await message.reply_text("⚠️ يرجى تحديد معرّف رقمي صحيح.\n مثال: `/unban 123456789`")
                return
        else:
            await message.reply_text(
                "📢 **طريقة الاستخدام:**\n\n"
                "• رد على رسالة المستخدم واكتب `/unban`\n"
                "• أو: `/unban <معرّف المستخدم>`"
            )
            return

        bh = BanHandler()
        if bh.unban(target_id):
            await message.reply_text(f"✅ تم رفع الحظر عن المستخدم `{target_id}` بنجاح.")
            logger.info(f"User {target_id} unbanned by {user_id}.")
        else:
            await message.reply_text(f"⚠️ المستخدم `{target_id}` غير محظور.")

    async def handle_banned_list(self, client: Client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        if not str(user_id) in self.env.AUTHORIZED_USER_ID:
            await message.reply_text("⛔ هذا الأمر متاح للمسؤول فقط.")
            return

        bh = BanHandler()
        banned = bh.all_banned()

        if not banned:
            await message.reply_text("✅ لا يوجد أي مستخدم محظور حالياً.")
            return

        lines = [f"🚫 **قائمة المحظورين** ({len(banned)})\n{'─' * 28}"]
        for rank, (uid, info) in enumerate(banned.items(), 1):
            date = info.get("banned_at", "")[:16]
            reason = info.get("reason", "")
            reason_part = f" | 📝 {reason}" if reason else ""
            lines.append(f"{rank}. `{uid}` — 🕐 {date}{reason_part}")

        text = "\n".join(lines)
        # Chunk if needed
        chunks, current = [], ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > 4096:
                chunks.append(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            chunks.append(current)

        for chunk in chunks:
            await client.send_message(message.chat.id, chunk)

    async def handle_delete(self, client: Client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        if not str(user_id) in self.env.AUTHORIZED_USER_ID:
            await message.reply_text("⛔ هذا الأمر متاح للمسؤول فقط.")
            return

        if not message.reply_to_message:
            await message.reply_text(
                "📢 **طريقة الاستخدام:**\n\n"
                "قم بالرد على رسالة الملف المحمّل واكتب `/delete`\n"
                "سيقوم البوت بحذف الملف من القرص."
            )
            return

        replied_id = message.reply_to_message.id
        db = FileDataHandler()
        file_path = db.get_download_file(replied_id)

        if not file_path:
            await message.reply_text(
                f"⚠️ لم يُعثر على ملف مرتبط بهذه الرسالة في قاعدة البيانات.\n"
                f"(معرّف الرسالة: `{replied_id}`)"
            )
            return

        file_name = os.path.basename(file_path)

        if not os.path.exists(file_path):
            await message.reply_text(
                f"⚠️ الملف غير موجود على القرص (ربما حُذف مسبقاً):\n`{file_path}`"
            )
            return

        try:
            file_size = os.path.getsize(file_path)
            os.remove(file_path)
            if file_size < 1024 ** 2:
                size_str = f"{file_size / 1024:.2f} KB"
            elif file_size < 1024 ** 3:
                size_str = f"{file_size / 1024 ** 2:.2f} MB"
            else:
                size_str = f"{file_size / 1024 ** 3:.2f} GB"

            logger.info(f"Deleted file: {file_path} by user {user_id}")
            await message.reply_text(
                f"🗑️ **تم حذف الملف بنجاح**\n\n"
                f"📄 **الاسم:** `{file_name}`\n"
                f"💾 **الحجم المُحرَّر:** {size_str}\n"
                f"📂 **المسار:** `{file_path}`"
            )
        except Exception as e:
            logger.error(f"handle_delete error: {e}")
            await message.reply_text(f"❌ فشل حذف الملف:\n`{e}`")

    async def handle_users(self, client: Client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        if not str(user_id) in self.env.AUTHORIZED_USER_ID:
            await message.reply_text("⛔ هذا الأمر متاح للمسؤول فقط.")
            return

        db = FileDataHandler()
        downloads = db.downloads

        if not downloads:
            await message.reply_text("⚠️ لا يوجد مستخدمون في قاعدة البيانات بعد.")
            return

        # Aggregate per user: count of files and latest download date
        user_stats = {}
        for record in downloads:
            uid = record.get("user_id")
            if not uid:
                continue
            date_str = record.get("download_date", "")
            if uid not in user_stats:
                user_stats[uid] = {"count": 0, "last": date_str}
            user_stats[uid]["count"] += 1
            if date_str > user_stats[uid]["last"]:
                user_stats[uid]["last"] = date_str

        # Sort by most recent activity
        sorted_users = sorted(user_stats.items(), key=lambda x: x[1]["last"], reverse=True)

        total_users = len(sorted_users)
        total_files = sum(v["count"] for v in user_stats.values())

        # Build paginated text (Telegram limit: 4096 chars)
        header = (
            f"👥 **قائمة المستخدمين**\n"
            f"إجمالي المستخدمين: **{total_users}** | إجمالي الملفات: **{total_files}**\n"
            f"{'─' * 30}\n"
        )
        lines = []
        for rank, (uid, info) in enumerate(sorted_users, 1):
            last = info["last"][:16] if info["last"] else "—"
            lines.append(f"{rank}. `{uid}` — 📁 {info['count']} ملف | 🕐 {last}")

        # Send in chunks of 4096 chars
        chunks = []
        current = header
        for line in lines:
            if len(current) + len(line) + 1 > 4096:
                chunks.append(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            chunks.append(current)

        for chunk in chunks:
            await client.send_message(message.chat.id, chunk)

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

