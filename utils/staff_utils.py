import discord
from typing import Optional, List

AUTO_ARCHIVE_DURATION = 3 * 24 * 60  # 3 days 


def get_user_id_from_thread(thread: discord.Thread) -> Optional[int]:
    """
    Extracts the User ID from the standardized thread name: '💬-name-ID'
    Ensures we don't need a DB to know who the thread belongs to.
    """
    try:
        return int(thread.name.rsplit('-', 1)[-1])
    except (ValueError, AttributeError):
        return None

def format_thread_name(user: discord.User) -> str:
    """Standardizes naming to ensure regex compatibility."""
    return f"{user.name}-{user.id}"

async def prepare_relay_files(message: discord.Message) -> List[discord.File]:
    """Converts message attachments to re-uploadable files."""
    return [await a.to_file() for a in message.attachments]

async def relay_content(destination: discord.abc.Messageable, 
                        message: discord.Message, message_cache: dict[int, int], before_message_id: Optional[int] = None) -> discord.Message:
    """
    The core relay logic. 
    Handles text, stickers, and files in one pass.
    """
    files = await prepare_relay_files(message)
    stickers = message.stickers or []
    content = f"{message.content}".strip()
    embeds = message.embeds or []
    
    if not content and not files and not stickers and not embeds:
        raise ValueError("Attempted to relay an empty message.")

    reference_message_id = message.reference and message.reference.message_id
    relayed_reference_id = message_cache.get(reference_message_id) if reference_message_id else None
    before_relay_id = message_cache.get(before_message_id) if before_message_id else None
        
    if before_relay_id:
        before_relayed_message = await destination.fetch_message(before_relay_id)
        msg = await before_relayed_message.edit(
            content=content,
            embeds=embeds,
            attachments=files,
        )
    else:
        msg = await destination.send(
            content=content,
            files=files,
            stickers=stickers,
            embeds=embeds,
            reference=discord.MessageReference(
                message_id=relayed_reference_id, 
                channel_id=destination.id  # <--- Added this
            ) if relayed_reference_id else None
)
    message_cache[message.id] = msg.id
    message_cache[msg.id] = message.id
    return msg

async def delete_relay(destination: discord.abc.Messageable, message_id: int, message_cache: dict[int, int]) -> bool:
    """Deletes a relayed message based on the original message ID."""
    relayed_id = message_cache.get(message_id)
    if not relayed_id:
        return False
    try:
        relayed_message = await destination.fetch_message(relayed_id)
        await relayed_message.delete() 
        del message_cache[message_cache.get(message_id)] 
        del message_cache[message_id]
    except discord.NotFound:
        return False
    return True

async def get_user_thread(forum: discord.ForumChannel, user: discord.User) -> Optional[discord.Thread]:
    """
    Stateless lookup. Searches active, then archived threads.
    If archived, it unarchives automatically.
    """
    target_name = format_thread_name(user)
    
    # Check active cache
    thread = discord.utils.get(forum.threads, name=target_name)
    
    if not thread:
        # Check recently archived
        async for arch in forum.archived_threads():
            if arch.name == target_name:
                thread = arch
                await thread.edit(archived=False, reason="New activity detected.")
                break
                
    if not thread:
        thread = await forum.create_thread(
            name=target_name,
            content=f"{user.mention} just DMed the bot!",
            reason="Starting new staff thread.",
            auto_archive_duration=AUTO_ARCHIVE_DURATION
        )
        thread = thread and thread.thread
    return thread

