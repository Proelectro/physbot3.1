# Command definitions with detailed descriptions

qotd_cmds_everyone = [
    (
        "/qotd fetch <num>",
        "Retrieve a past Question of the Day by its number.",
    ),
    (
        "/qotd solution <num>",
        "Display the official solution and answer for a specific QOTD.",
    ),
    (
        "/qotd submit <answer> [num]",
        "Submit your answer for the live or specified QOTD via DM. Cooldown: 30 seconds.",
    ),
    (
        "/qotd verify_submission <num>",
        "Verify your submissions for an active QOTD via DM.",
    ),
    (
        "/qotd score [user]",
        "View the detailed score transcript for yourself or another user.",
    ),
    (
        "/qotd random [topic] [curator] [difficulty]",
        "Fetch a random QOTD matching the optional filters.",
    ),
    (
        "/qotd help",
        "Display the list of QOTD commands available to you.",
    ),
]

qotd_cmds_creator = [
    (
        "/qotd start",
        "Start a new QOTD season.",
    ),
    (
        "/qotd change_time <hour> <minute> [timezone]",
        "Change the daily posting time of the QOTD.",
    ),
    (
        "/qotd upload <question> <topic> <answer> <difficulty> <source> [tolerance] [points]",
        "Upload a new QOTD for review.",
    ),
    (
        "/qotd update_solution <num> <solution>",
        "Upload or replace the solution attachment for a QOTD.",
    ),
    (
        "/qotd update_leaderboard",
        "Recalculate the leaderboard for the current live QOTD.",
    ),
    (
        "/qotd pending [num]",
        "View pending QOTDs awaiting review or scheduling.",
    ),
    (
        "/qotd edit <num> [fields...]",
        "Edit an existing QOTD.",
    ),
    (
        "/qotd get_submission <user> <num>",
        "View the submissions of a user for a QOTD.",
    ),
    (
        "/qotd update_submission <user> <num> <submission>",
        "Overwrite a user's submission for a QOTD.",
    ),
    (
        "/qotd update_offset <user> <offset>",
        "Update the manual score offset of a user.",
    ),
    (
        "/qotd clear_submissions <num> [user]",
        "Clear submissions for a user or everyone for a QOTD.",
    ),
    (
        "/qotd clear_cache",
        "Reload the QOTD cache. Owner only.",
    ),
    (
        "/qotd end_season",
        "End the current QOTD season. Owner only.",
    ),
]

potd_cmds_everyone = [
    (
        "/potd fetch <num>",
        "Retrieve a past Problem of the Day by its number.",
    ),
    (
        "/potd solution <num>",
        "Display the official solution for a POTD.",
    ),
    (
        "/potd submit <solution> [num]",
        "Submit your solution for the live or specified POTD via DM. Cooldown: 30 seconds.",
    ),
    (
        "/potd random [topic] [curator] [difficulty]",
        "Fetch a random POTD matching the optional filters.",
    ),
    (
        "/potd help",
        "Display the list of POTD commands available to you.",
    ),
]

potd_cmds_creator = [
    (
        "/potd upload <problem> <topic> <difficulty> <source> <points>",
        "Upload a new POTD for review.",
    ),
    (
        "/potd update_solution <num> <link>",
        "Update the solution for a POTD.",
    ),
    (
        "/potd add_score <num> <user> <points> [user_id]",
        "Manually award points for a POTD.",
    ),
    (
        "/potd update_leaderboard <num>",
        "Recalculate the leaderboard for a POTD.",
    ),
    (
        "/potd pending [num]",
        "View pending POTDs awaiting review or scheduling.",
    ),
    (
        "/potd edit <num> [fields...]",
        "Edit an existing POTD.",
    ),
    (
        "/potd clear_cache",
        "Reload the POTD cache. Owner only.",
    ),
    (
        "/potd check",
        "Internal consistency check. Owner only.",
    ),
]

cmds_staff = [
    (
        "/staff help",
        "Display the list of available staff commands.",
    ),
    (
        "/staff clear_cache",
        "Reload the staff cache. Owner only.",
    ),
    (
        "/message <text> [channel/user id] [reply id]",
        "Send a message through the bot.",
    ),
    (
        "/edit_message <new_content> <message_id> [channel_id]",
        "Edit a message previously sent by the bot.",
    ),
    (
        "/remove_role <role>",
        "Remove a role from every member who currently has it.",
    ),
]