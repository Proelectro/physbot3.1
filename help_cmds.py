# Command definitions with detailed descriptions
cmds_everyone = [
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
    )
]
cmds_creator = [
    (
        "/qotd upload <links> <topic> <answer> <difficulty> [tolerance] [source] [points]",
        "Add a new QOTD to the planning queue. Provide one or more image URLs, the topic, the correct numeric answer, difficulty (e.g., easy/medium/hard), optional tolerance percentage, source reference, and legacy points field.",
    ),
    (
        "/qotd update_solution <num> <link>",
        "Upload or correct the solution image/ pdf link(s) for an existing QOTD. Use this if the solution is wrong or missing.",
    ),
    (
        "/qotd pending <num>",
        "List QOTD uploads awaiting approval or scheduling. Optionally filter by question number to see details of a specific pending item.",
    ),
    (
        "/qotd update_leaderboard",
        "Recalculate and post the leaderboard for the current live QOTD. Updates ranks based on recent submissions according to scoring rules.",
    ),
    (
        "/qotd get_submissions <user> <num>",
        "Get the submissions of a specific user for a specific QOTD.",
    )
]
