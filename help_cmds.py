# Command definitions with detailed descriptions
qotd_cmds_everyone = [
    (
        "/qotd fetch <num>",
        "Retrieves a past Question of the Day by its number. Useful for reviewing old questions or discussion archives.",
    ),
    (
        "/qotd solution <num>",
        "Displays the official solution and accepted answer for a specific QOTD. Great for checking the correct approach or explanation.",
    ),
    (
        "/qotd submit <answer> [num]",
        "Submit your answer to the current or specified QOTD via DM. If no number is given, your answer will apply to the live question. Cooldown: 30s.",
    ),
    (
        "/qotd help",
        "Shows this help message, listing all available QOTD commands you have permission to use.",
    ),
    (
        "/qotd verify_submission [num]",
        "Verify the receipt and validity of a submitted answer for any active QOTD (i.e. any QOTD of current season defaults to live if no arg given) via DM.",
    ),
    (
        "/qotd score [user]",
        "Get a detailed transcript of a user's QOTD score history. Defaults to your own score if no user is mentioned.",
    ),
    (
        "/qotd faq [num]",
        "For experianced user to give a quick reply to common questions.",
    ),
    (
        "/qotd random [topic] [curator] [difficulty]",
        "Fetch a random QOTD based on optional filters like topic, curator, or difficulty. If no filters are provided, it returns any random QOTD.",
    ),
]
qotd_cmds_creator = [
    (
        "/qotd upload <problem> <topic> <answer> <difficulty> [tolerance] [source] [points]",
        "Add a new QOTD to the planning queue. Provide question image as an attachment, the topic, the correct numeric answer, difficulty (e.g., easy/medium/hard), optional tolerance percentage, source reference, and legacy points field.",
    ),
    (
        "/qotd update_solution <num> <link>",
        "Upload or correct the solution image/ pdf link(s) for an existing QOTD. Use this if the solution is wrong or missing.",
    ),
    (
        "/qotd pending [num]",
        "List QOTD uploads awaiting approval or scheduling. Optionally filter by question number to see details of a specific pending item.",
    ),
    (
        "/qotd update_leaderboard",
        "Recalculate and post the leaderboard for the current live QOTD. Updates ranks based on recent submissions according to scoring rules.",
    ),
    (
        "/qotd get_submissions <user> <num>",
        "Get the submissions of a specific user for a specific QOTD.",
    ),
    (
        "/qotd update_submission <user> <num> <new_submission(s)>",
        "Update the submission for a specific user and QOTD with a new answer. New submissions can be a single answer or multiple answers separated by commas. Example: /qotd update_submission @user 5 42,43,44",
    ),
    (
        "/qotd clear_submissions <num> [user]",
        "Clear all submissions for a specific user and QOTD. Clears all submissions if no user is specified."
    )
]

potd_cmds_everyone = [
    (
        "/potd fetch <num>",
        "Retrieves a past Problem of the Day by its number. Useful for reviewing old questions or discussion archives.",
    ),
    (
        "/potd solution <num>",
        "Displays the official solution for a specific POTD. Great for checking the correct approach or explanation.",
    ),
    (
        "/potd submit <solution> [num]",
        "Submit your solution to the current or specified POTD via DM. If no number is given, your solution will apply to the live problem. Cooldown: 30s.",
    ),
    (
        "/potd help",
        "Shows this help message, listing all available POTD commands you have permission to use.",
    ),
    (
        "/potd random [topic] [curator] [difficulty]",
        "Fetch a random POTD based on optional filters like topic, curator, or difficulty. If no filters are provided, it returns any random POTD.",
    ),
]

potd_cmds_creator = [
    (
        "/potd upload <problem> <topic> <points> <difficulty> [source]",
        "Add a new POTD to the planning queue. Attach problem image, difficulty (e.g., 1/2/3/4/5), source reference, and points.",
    ),
    (
        "/potd update_solution <num> <link>",
        "Upload or correct the solution image/ pdf link(s) for an existing POTD. Use this if the solution is wrong or missing.",
    ),
    (
        "/potd pending [num]",
        "List POTD uploads awaiting approval or scheduling. Optionally filter by question number to see details of a specific pending item.",
    ),
    (
        "/potd update_leaderboard <num>",
        "Recalculate and post the leaderboard for the specified POTD.",
    ),
    (
        "/potd add_score <num> <user> <score> [user_id]",
        "Manually add a score for a user's submission to a specific POTD. Specify the problem number, user (mention or ID), and the score to be added.",
    ),
    (
        "/potd edit <num> [fields to edit]",
        "Edit the details of an existing POTD. Specify the problem number and the fields you want to update (e.g., topic, difficulty, source). This allows curators to correct or improve POTD information after it's been uploaded.",
    )
]

cmds_staff = [
    (
        "/staff help",
        "Shows this help message, listing all available Staff commands you have permission to use.",
    ),
    (
        "/staff monitor [channel] [user]",
        "Monitor a specific channel to send and receive messages through the bot. If both specified it will monitor DM of the user and channel. If no channel is specified it will list all monitored channels. If already monitoring the channel, it will stop monitoring it.",
    ),
]
        