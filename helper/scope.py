def get_scope_id(message):
    """
    Return the settings key for a message.

    Private chat: user ID
    Broadcast channel: channel ID
    Group/supergroup: sender ID when available
    """
    chat = getattr(message, "chat", None)
    user = getattr(message, "from_user", None)

    if chat:
        chat_type = getattr(chat, "type", None)
        type_name = str(getattr(chat_type, "value", chat_type)).lower()

        if type_name.endswith("channel"):
            return int(chat.id)

    if user:
        return int(user.id)

    if chat:
        return int(chat.id)

    raise ValueError("Could not determine the settings ID for this message.")
