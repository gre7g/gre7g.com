from types_boto3_dynamodb.service_resource import Table as DynamoDBTable

from database import Product, ProductId, Filename

# Constants:
SKELETON_CREW = 9
SMALL_WORLD = 3
FAIR_TRADE = 5
NOBODY_LEFT_BEHIND = 46
REAPERS_LOTTERY = 9
EXECUTIONERS_GAMBIT = 11
TALES_OF_HAYVEN_CELESTIA_1 = 12
TALES_OF_HAYVEN_CELESTIA_2 = 21
HAYVEN_CELESTIA_PIN = 3

PRODUCTS = [
    Product(
        "Kanti Cycle 1: Skeleton Crew",
        "Kanti Cycle 1: Skeleton Crew",
        """
            <p>
                A slave raised believing himself free, a criminal even before his birth. Everyone thinks Kanti is 
                someone he isn’t: a playboy reduced to working at the dump, a spiteful son trying to make amends, and 
                perhaps even an excuse to recycle every last officer, crewman, and cub on board.
            </p>
            <p> 
                However, this unlikely hero and the rest of the crew are in for a wild ride to the brink of mutiny, 
                isolated deep in space, some 1,500 light years from home. When the sinister Commissioner Sarsuk starts 
                tightening restrictions on birth tokens for the geroo colony, Kanti is forced to make decisions about 
                his identity … and his place in the colony he hopes to always call home, even if at the risk of family, 
                friends, and love.
            </p>
            <p>SciFi / Action</p>
            """,
        "/shop/books/skeleton-crew",
        ProductId("kc1"),
        images=["/static/images/products/skeleton-crew-1.jpg"],
        media="paperback, ebook, audiobook",
        child_ids=[ProductId("kc1-paperback"), ProductId("kc1-ebook"), ProductId("kc1-audiobook")],
    ),
    Product(
        "Skeleton Crew − paperback",
        "Kanti Cycle 1: Skeleton Crew (paperback, action/adventure sci-fi novel)",
        "<p>220 pages, Illustrated</p>",
        "/shop/books/skeleton-crew/paperback",
        ProductId("kc1-paperback"),
        SKELETON_CREW,
        13.99,
        [
            "/static/images/products/skeleton-crew-1.jpg",
            "/static/images/products/skeleton-crew-2.jpg",
            "/static/images/products/skeleton-crew-3.jpg",
            "/static/images/products/skeleton-crew-4.jpg",
            "/static/images/products/skeleton-crew-5.jpg",
        ],
        media="paperback",
        parent_id=ProductId("kc1"),
    ),
    Product(
        "Skeleton Crew − ebook",
        "Kanti Cycle 1: Skeleton Crew (paperback, action/adventure sci-fi novel)",
        """
            <p>220 pages, Illustrated</p>
            <p>Download includes all three DRM-free versions:</p>
            <ul>
                <li>.epub format</li>
                <li>.mobi format</li>
                <li>.pdf format</li>
            </ul>
            """,
        "/shop/books/skeleton-crew/ebook",
        ProductId("kc1-ebook"),
        -1,
        4.99,
        [
            "/static/images/products/skeleton-crew-1.jpg",
            "/static/images/products/skeleton-crew-6.jpg",
            "/static/images/products/skeleton-crew-7.jpg",
        ],
        {
            Filename("KC1SkeletonCrew.epub"): None,
            Filename("KC1SkeletonCrew.mobi"): None,
            Filename("KC1SkeletonCrew.pdf"): None,
        },
        "ebook",
        parent_id=ProductId("kc1"),
    ),
    Product(
        "Skeleton Crew − audiobook",
        "Kanti Cycle 1: Skeleton Crew (paperback, action/adventure sci-fi novel)",
        """
            <p>6 hours, 52 minutes</p>
            <p>Voiced by the amazing Piers Ryman</p>
            <p>Digital download is a .zip of DRM-free .mp3 files</p>
            """,
        "/shop/books/skeleton-crew/audiobook",
        ProductId("kc1-audiobook"),
        -1,
        16.11,
        ["/static/images/products/skeleton-crew-1.jpg"],
        {Filename("KC1SkeletonCrew.zip"): None},
        "audiobook",
        parent_id=ProductId("kc1"),
    ),
    Product(
        "Kanti Cycle 2: Small World",
        "Kanti Cycle 2: Small World",
        """
            <p>
                The commissioner accidentally let his last cleaning crew starve to death. So now, Kanti and forty-nine 
                of his teammates will have to spend the rest of their lives living in a one-room barracks with only a 
                single airlock protecting them from the planet's poisonous atmosphere. 
            </p>
            <p>
                Surrounded by towering monsters, on a world where the very air is lethal, mysterious burrowing strangers 
                are pushing the crew into a panic. Will Kanti be able to keep them from tearing each other apart? Or are 
                they doomed to suffer a fate similar to the commissioner's previous cleaning crew?
            </p>
            <p>SciFi / Action</p>
            """,
        "/shop/books/small-world",
        ProductId("kc2"),
        images=["/static/images/products/small-world-1.jpg"],
        media="paperback, ebook, audiobook",
        child_ids=[ProductId("kc2-paperback"), ProductId("kc2-ebook"), ProductId("kc2-audiobook")],
    ),
    Product(
        "Small World − paperback",
        "Kanti Cycle 2: Small World (paperback, action/adventure sci-fi novel)",
        "<p>300 pages, Illustrated</p>",
        "/shop/books/small-world/paperback",
        ProductId("kc2-paperback"),
        3,
        15.99,
        [
            "/static/images/products/small-world-1.jpg",
            "/static/images/products/small-world-4.jpg",
            "/static/images/products/small-world-5.jpg",
            "/static/images/products/small-world-6.jpg",
            "/static/images/products/small-world-7.jpg",
        ],
        media="paperback",
        parent_id=ProductId("kc2"),
    ),
    Product(
        "Small World − ebook",
        "Kanti Cycle 2: Small World (ebook, action/adventure sci-fi novel)",
        """
            <p>300 pages, Illustrated</p>
            <p>Download includes all three DRM-free versions:</p>
            <ul>
                <li>.epub format</li>
                <li>.mobi format</li>
                <li>.pdf format</li>
            </ul>
            """,
        "/shop/books/small-world/ebook",
        ProductId("kc2-ebook"),
        -1,
        5.99,
        [
            "/static/images/products/small-world-1.jpg",
            "/static/images/products/small-world-2.jpg",
            "/static/images/products/small-world-3.jpg",
        ],
        {
            Filename("KC2SmallWorld.epub"): None,
            Filename("KC2SmallWorld.mobi"): None,
            Filename("KC2SmallWorld.pdf"): None,
        },
        "ebook",
        parent_id=ProductId("kc2"),
    ),
    Product(
        "Small World − audiobook",
        "Kanti Cycle 2: Small World (audiobook, action/adventure sci-fi novel)",
        """
            <p>7 hours, 49 minutes</p>
            <p>Voiced by the amazing Piers Ryman</p>
            <p>Digital download is a .zip of DRM-free .mp3 files</p>
            """,
        "/shop/books/small-world/audiobook",
        ProductId("kc2-audiobook"),
        -1,
        17.40,
        ["/static/images/products/small-world-1.jpg"],
        {Filename("KC2SmallWorld.zip"): None},
        "audiobook",
        parent_id=ProductId("kc2"),
    ),
    Product(
        "Kanti Cycle 3: Fair Trade",
        "Kanti Cycle 3: Fair Trade",
        """
            <p>
                Kanti had spent many sleepless nights torturing himself with thoughts of the day when he would give up 
                on returning to Tish. Old and gray, back stooped from decades of labor, he would try to get up out of 
                bed, and change his mind. Why bother?
            </p>
            <p>
                He couldn’t have been more wrong. He was still young, his pelt still tan, and his back didn’t hurt when 
                he rose.
            </p>
            <p>
                Everything had conspired to keep the two lovers apart: rivals, foes, distance. Now, he needs his 
                friends’ help more than ever if he wants his old life back.
            </p>
            <p>SciFi / Action</p>
            """,
        "/shop/books/fair-trade",
        ProductId("kc3"),
        images=["/static/images/products/fair-trade-1.jpg"],
        media="paperback, ebook, audiobook",
        child_ids=[ProductId("kc3-paperback"), ProductId("kc3-ebook"), ProductId("kc3-audiobook")],
    ),
    Product(
        "Fair Trade − paperback",
        "Kanti Cycle 3: Fair Trade (paperback, action/adventure sci-fi novel)",
        "<p>334 pages, Illustrated</p>",
        "/shop/books/fair-trade/paperback",
        ProductId("kc3-paperback"),
        FAIR_TRADE,
        17.99,
        [
            "/static/images/products/fair-trade-1.jpg",
            "/static/images/products/fair-trade-2.jpg",
            "/static/images/products/fair-trade-3.jpg",
            "/static/images/products/fair-trade-4.jpg",
            "/static/images/products/fair-trade-5.jpg",
        ],
        media="paperback",
        parent_id=ProductId("kc3"),
    ),
    Product(
        "Fair Trade − ebook",
        "Kanti Cycle 3: Fair Trade (ebook, action/adventure sci-fi novel)",
        """
            <p>334 pages, Illustrated</p>
            <p>Download includes all three DRM-free versions:</p>
            <ul>
                <li>.epub format</li>
                <li>.mobi format</li>
                <li>.pdf format</li>
            </ul>
            """,
        "/shop/books/fair-trade/ebook",
        ProductId("kc3-ebook"),
        -1,
        6.99,
        [
            "/static/images/products/fair-trade-1.jpg",
            "/static/images/products/fair-trade-6.jpg",
            "/static/images/products/fair-trade-7.jpg",
        ],
        {
            Filename("KC3FairTrade.epub"): None,
            Filename("KC3FairTrade.mobi"): None,
            Filename("KC3FairTrade.pdf"): None,
        },
        "ebook",
        parent_id=ProductId("kc3"),
    ),
    Product(
        "Fair Trade − audiobook",
        "Kanti Cycle 3: Fair Trade (audiobook, action/adventure sci-fi novel)",
        """
            <p>12 hours, 43 minutes</p>
            <p>Voiced by the amazing Piers Ryman</p>
            <p>Digital download is a .zip of DRM-free .mp3 files</p>
            """,
        "/shop/books/fair-trade/audiobook",
        ProductId("kc3-audiobook"),
        -1,
        21.83,
        ["/static/images/products/fair-trade-1.jpg"],
        {Filename("KC3FairTrade.zip"): None},
        "audiobook",
        parent_id=ProductId("kc3"),
    ),
    Product(
        "Kanti Cycle 3.5: Nobody Left Behind",
        "Kanti Cycle 3.5: Nobody Left Behind",
        """
            <p>
                “My captors, you mean,” scoffed Commissioner Sarsuk. His solid green eyes glared from behind his scaled
                face. “It’s not like I can leave.”
            </p>
            <p>
                The geroo’s long ears spread slightly. “You’re free to go. Go.”
            </p>
            <p> 
                “Cute,” he sneered. “I’m so glad you take enjoyment from my pain.”
            </p>
            <p>
                The nasty ol’ krakun that everyone loves to hate has got himself in a bit of a bind. He’s stuck in his 
                apartment, forgotten, and without a friend in sight. To escape the trap, this particular nobody will 
                need to do the impossible.
            </p>
            <p>SciFi / Intrigue</p>
            """,
        "/shop/books/nobody-left-behind",
        ProductId("kc3.5"),
        images=["/static/images/products/nobody-left-behind-4.jpg"],
        media="paperback, ebook, audiobook",
        child_ids=[ProductId("kc3.5-paperback"), ProductId("kc3.5-ebook"), ProductId("kc3.5-audiobook")],
    ),
    Product(
        "Nobody Left Behind − paperback",
        "Kanti Cycle 3.5: Nobody Left Behind (paperback, action/adventure sci-fi novel)",
        "<p>228 pages, Illustrated</p>",
        "/shop/books/nobody-left-behind/paperback",
        ProductId("kc3.5-paperback"),
        NOBODY_LEFT_BEHIND,
        19.99,
        [
            "/static/images/products/nobody-left-behind-1.jpg",
            "/static/images/products/nobody-left-behind-2.jpg",
            "/static/images/products/nobody-left-behind-3.jpg",
        ],
        media="paperback",
        parent_id=ProductId("kc3.5"),
    ),
    Product(
        "Nobody Left Behind − ebook",
        "Kanti Cycle 3.5: Nobody Left Behind (ebook, action/adventure sci-fi novel)",
        """
            <p>228 pages, Illustrated</p>
            <p>Download includes all three DRM-free versions:</p>
            <ul>
                <li>.epub format</li>
                <li>.mobi format</li>
                <li>.pdf format</li>
            </ul>
            """,
        "/shop/books/nobody-left-behind/ebook",
        ProductId("kc3.5-ebook"),
        -1,
        9.99,
        [
            "/static/images/products/nobody-left-behind-4.jpg",
            "/static/images/products/nobody-left-behind-5.jpg",
            "/static/images/products/nobody-left-behind-6.jpg",
        ],
        {
            Filename("KC3.5NobodyLeftBehind.epub"): None,
            Filename("KC3.5NobodyLeftBehind.mobi"): None,
            Filename("KC3.5NobodyLeftBehind.pdf"): None,
        },
        "ebook",
        parent_id=ProductId("kc3.5"),
    ),
    Product(
        "Nobody Left Behind − audiobook",
        "Kanti Cycle 3.5: Nobody Left Behind (audiobook, action/adventure sci-fi novel)",
        """
            <p>6 hours, 50 minutes</p>
            <p>Voiced by the amazing Piers Ryman</p>
            <p>Digital download is a .zip of DRM-free .mp3 files</p>
            """,
        "/shop/books/nobody-left-behind/audiobook",
        ProductId("kc3.5-audiobook"),
        -1,
        16.11,
        ["/static/images/products/nobody-left-behind-4.jpg"],
        {Filename("KC3.5NobodyLeftBehind.zip"): None},
        "audiobook",
        parent_id=ProductId("kc3.5"),
    ),
    Product(
        "Tori Mysteries 1: Reaper's Lottery",
        "Tori Mysteries 1: Reaper's Lottery",
        """
            <p>
                “They’ve put Kaz on trial for the murders!” cried Aziz. “They’re going to execute her as the killer!”
            </p>
            <p>
                Tori shook her head in an attempt to wake more fully. “What? No. That’s a mistake. Kaz wouldn’t harm an 
                insect. There’s no way a court could find her guilty.”
            </p>
            <p>
                “The krakun legal system doesn’t give a damn about geroo. They find <i>everyone</i> guilty!”
            </p>
            <p>
                Their first-ever serial killer is stalking the crew, and though the Reaper’s Harvest III is a high-tech 
                starship, Tori has no access to any forensic science. If she wants to save her best friend’s life, she 
                needs to think of a new way to solve the crimes … and fast!
            </p>
            <p>SciFi / Mystery</p>
            """,
        "/shop/books/reapers-lottery",
        ProductId("tm1"),
        images=["/static/images/products/reapers-lottery-1.jpg"],
        media="paperback, ebook, audiobook",
        child_ids=[ProductId("tm1-paperback"), ProductId("tm1-ebook"), ProductId("tm1-audiobook")],
    ),
    Product(
        "Reaper's Lottery − paperback",
        "The Tori Mysteries 1: Reaper's Lottery (paperback, mystery sci-fi novel)",
        "<p>432 pages, Illustrated</p>",
        "/shop/books/reapers-lottery/paperback",
        ProductId("tm1-paperback"),
        REAPERS_LOTTERY,
        16.99,
        [
            "/static/images/products/reapers-lottery-1.jpg",
            "/static/images/products/reapers-lottery-4.jpg",
            "/static/images/products/reapers-lottery-5.jpg",
            "/static/images/products/reapers-lottery-6.jpg",
            "/static/images/products/reapers-lottery-7.jpg",
        ],
        media="paperback",
        parent_id=ProductId("tm1"),
    ),
    Product(
        "Reaper's Lottery − ebook",
        "The Tori Mysteries 1: Reaper's Lottery (ebook, mystery sci-fi novel)",
        """
            <p>432 pages, Illustrated</p>
            <p>Download includes all three DRM-free versions:</p>
            <ul>
                <li>.epub format</li>
                <li>.mobi format</li>
                <li>.pdf format</li>
            </ul>
            """,
        "/shop/books/reapers-lottery/ebook",
        ProductId("tm1-ebook"),
        -1,
        7.99,
        [
            "/static/images/products/reapers-lottery-1.jpg",
            "/static/images/products/reapers-lottery-2.jpg",
            "/static/images/products/reapers-lottery-3.jpg",
        ],
        {
            Filename("TM1ReapersLottery.epub"): None,
            Filename("TM1ReapersLottery.mobi"): None,
            Filename("TM1ReapersLottery.pdf"): None,
        },
        "ebook",
        parent_id=ProductId("tm1"),
    ),
    Product(
        "Reaper's Lottery − audiobook",
        "The Tori Mysteries 1: Reaper's Lottery (audiobook, mystery sci-fi novel)",
        """
            <p>10 hours, 58 minutes</p>
            <p>Voiced by the amazing Piers Ryman</p>
            <p>Digital download is a .zip of DRM-free .mp3 files</p>
            """,
        "/shop/books/reapers-lottery/audiobook",
        ProductId("tm1-audiobook"),
        -1,
        20.62,
        ["/static/images/products/reapers-lottery-1.jpg"],
        {Filename("TM1ReapersLottery.zip"): None},
        "audiobook",
        parent_id=ProductId("tm1"),
    ),
    Product(
        "Tori Mysteries 2: Executioner's Gambit",
        "Tori Mysteries 2: Executioner's Gambit",
        """
            <p>
                Tori stared at the screen. "Wait, what? How long is three hundred and fifty-five hours?"
            </p>
            <p>
                "It's about fifteen days, Tori," the commissioner sighed. "If we don't get the trinity back online 
                within fifteen days—give or take—there won't be enough power capacity left to bring it back up, and the 
                reactor will be past the point of no return. Without the reactor, this ship is going to get very cold, 
                and everyone will freeze to death."
            </p>
            <p>
                Desperate to get the surgery she needs, Tori transfers aboard the Sailor's Gambit I to catch a 
                vigilante. But the situation quickly unravels, and our unlikely investigator discovers that a serial 
                killer on the loose is the very least of her problems.
            </p>
            <p>SciFi / Mystery</p>
            """,
        "/shop/books/executioners-gambit",
        ProductId("tm2"),
        images=["/static/images/products/executioners-gambit-1.jpg"],
        media="paperback, ebook, audiobook",
        child_ids=[ProductId("tm2-paperback"), ProductId("tm2-ebook"), ProductId("tm2-audiobook")],
    ),
    Product(
        "Executioner's Gambit − paperback",
        "The Tori Mysteries 2: Executioner's Gambit (paperback, mystery sci-fi novel)",
        "<p>493 pages, Illustrated</p>",
        "/shop/books/executioners-gambit/paperback",
        ProductId("tm2-paperback"),
        EXECUTIONERS_GAMBIT,
        22.99,
        [
            "/static/images/products/executioners-gambit-1.jpg",
            "/static/images/products/executioners-gambit-2.jpg",
            "/static/images/products/executioners-gambit-3.jpg",
            "/static/images/products/executioners-gambit-4.jpg",
            "/static/images/products/executioners-gambit-5.jpg",
        ],
        media="paperback",
        parent_id=ProductId("tm2"),
    ),
    Product(
        "Executioner's Gambit − ebook",
        "The Tori Mysteries 2: Executioner's Gambit (ebook, mystery sci-fi novel)",
        """
            <p>493 pages, Illustrated</p>
            <p>Download includes all three DRM-free versions:</p>
            <ul>
                <li>.epub format</li>
                <li>.mobi format</li>
                <li>.pdf format</li>
            </ul>
            """,
        "/shop/books/executioners-gambit/ebook",
        ProductId("tm2-ebook"),
        -1,
        9.99,
        [
            "/static/images/products/executioners-gambit-6.jpg",
            "/static/images/products/executioners-gambit-7.jpg",
            "/static/images/products/executioners-gambit-8.jpg",
        ],
        {
            Filename("TM2ExecutionersGambit.epub"): None,
            Filename("TM2ExecutionersGambit.mobi"): None,
            Filename("TM2ExecutionersGambit.pdf"): None,
        },
        "ebook",
        parent_id=ProductId("tm2"),
    ),
    Product(
        "Executioner's Gambit − audiobook",
        "The Tori Mysteries 2: Executioner's Gambit (audiobook, mystery sci-fi novel)",
        """
            <p>14 hours, 2 minutes</p>
            <p>Voiced by the amazing Piers Ryman</p>
            <p>Digital download is a .zip of DRM-free .mp3 files</p>
            """,
        "/shop/books/executioners-gambit/audiobook",
        ProductId("tm2-audiobook"),
        -1,
        23.39,
        ["/static/images/products/executioners-gambit-1.jpg"],
        {Filename("TM2ExecutionersGambit.zip"): None},
        "audiobook",
        parent_id=ProductId("tm2"),
    ),
    Product(
        "Long Way Home",
        "Long Way Home",
        """
            <p>
                18+ AUDIENCE ONLY
            </p>
            <p>
                Jungo left the farm in search of action and adventure—and he found both in space. From a ship full of 
                horny pirates to a repressed slave girl, his future holds a lot more than he bargained for!
            </p>
            <p>
                Too hot for Amazon! SciFi / Erotica
            </p>
            <p>
                ● M/F ● M/M ● Group Sex ●
            </p>
            """,
        "/shop/books/long-way-home",
        ProductId("lwh"),
        images=["/static/images/products/long-way-home-1.jpg"],
        media="paperback, ebook, audiobook",
        child_ids=[ProductId("lwh-paperback"), ProductId("lwh-ebook"), ProductId("lwh-audiobook")],
    ),
    Product(
        "Long Way Home − paperback",
        "Long Way Home (paperback, erotica/adventure sci-fi novel)",
        "<p>292 pages, Explicit Illustrations</p>",
        "/shop/books/long-way-home/paperback",
        ProductId("lwh-paperback"),
        83,
        18.49,
        [
            "/static/images/products/long-way-home-1.jpg",
            "/static/images/products/long-way-home-3.jpg",
            "/static/images/products/long-way-home-4.jpg",
            "/static/images/products/long-way-home-5.jpg",
            "/static/images/products/long-way-home-6.jpg",
        ],
        media="paperback",
        parent_id=ProductId("lwh"),
    ),
    Product(
        "Long Way Home − ebook",
        "Long Way Home (ebook, erotica/adventure sci-fi novel)",
        """
            <p>292 pages, Explicit Illustrations</p>
            <p>Download includes all three DRM-free versions:</p>
            <ul>
                <li>.epub format</li>
                <li>.mobi format</li>
                <li>.pdf format</li>
            </ul>
            """,
        "/shop/books/long-way-home/ebook",
        ProductId("lwh-ebook"),
        -1,
        8.99,
        [
            "/static/images/products/long-way-home-1.jpg",
            "/static/images/products/long-way-home-2.jpg",
            "/static/images/products/long-way-home-7.jpg",
        ],
        {Filename("LongWayHome.epub"): None, Filename("LongWayHome.mobi"): None, Filename("LongWayHome.pdf"): None},
        "ebook",
        parent_id=ProductId("lwh"),
    ),
    Product(
        "Long Way Home − audiobook",
        "Long Way Home (audiobook, erotica/adventure sci-fi novel)",
        """
            <p>8 hours, 45 minutes</p>
            <p>Voiced by the amazing Piers Ryman</p>
            <p>Digital download is a .zip of DRM-free .mp3 files</p>
            """,
        "/shop/books/long-way-home/audiobook",
        ProductId("lwh-audiobook"),
        -1,
        18.83,
        ["/static/images/products/long-way-home-1.jpg"],
        {Filename("LongWayHome.zip"): None},
        "audiobook",
        parent_id=ProductId("lwh"),
    ),
    Product(
        "Tales of Hayven Celestia 1",
        "Tales of Hayven Celestia 1",
        """
            <p>
                Something long and sinuous eclipsed the searing sunlight. Lifeless and limp, the krakun captain of his 
                vessel spiraled nearby. His commander. His better. His god.
            </p>
            <p>
                He failed. Failure. Unworthy.
            </p>
            <p>
                He'd run. The breeching pod had come through the wall, and he'd run. The laser at his hip had never even 
                cleared the holster. He'd seen the look of disgust on his commander's face as he'd gone past in the 
                opposite direction. Coward. Puppy. Worthless. Then something hit the hull, and whipping atmosphere 
                carried him out into the freezing, burning void of empty space.
            </p>
            <p>
                "Tales of Hayven Celestia" features thirteen stories of ordinary people in extraordinary circumstances 
                far beyond their making or control. They will succeed or fail by only the thinnest of margins, and the 
                stakes have never been higher. They are gambling not only with their own lives but their whole 
                worlds—everyone they have ever met and even some they haven't.
            </p>
            <p>
                SciFi / Short Stories
            </p>
            """,
        "/shop/books/tales-of-hayven-celestia-1",
        ProductId("tohc1"),
        images=["/static/images/products/tales-of-hayven-celestia-1-1.jpg"],
        media="paperback, ebook, audiobook",
        child_ids=[ProductId("tohc1-paperback"), ProductId("tohc1-ebook"), ProductId("tohc1-audiobook")],
    ),
    Product(
        "Tales of Hayven Celestia 1 − paperback",
        "Tales of Hayven Celestia 1 (paperback, short-stories sci-fi anthology)",
        "<p>419 pages, Illustrated</p>",
        "/shop/books/tales-of-hayven-celestia-1/paperback",
        ProductId("tohc1-paperback"),
        TALES_OF_HAYVEN_CELESTIA_1,
        18.95,
        [
            "/static/images/products/tales-of-hayven-celestia-1-1.jpg",
            "/static/images/products/tales-of-hayven-celestia-1-4.jpg",
            "/static/images/products/tales-of-hayven-celestia-1-5.jpg",
            "/static/images/products/tales-of-hayven-celestia-1-6.jpg",
        ],
        media="paperback",
        parent_id=ProductId("tohc1"),
    ),
    Product(
        "Tales of Hayven Celestia 1 − ebook",
        "Tales of Hayven Celestia 1 (ebook, short-stories sci-fi anthology)",
        """
            <p>419 pages, Illustrated</p>
            <p>Download includes all three DRM-free versions:</p>
            <ul>
                <li>.epub format</li>
                <li>.mobi format</li>
                <li>.pdf format</li>
            </ul>
            """,
        "/shop/books/tales-of-hayven-celestia-1/ebook",
        ProductId("tohc1-ebook"),
        -1,
        8.99,
        [
            "/static/images/products/tales-of-hayven-celestia-1-1.jpg",
            "/static/images/products/tales-of-hayven-celestia-1-2.jpg",
            "/static/images/products/tales-of-hayven-celestia-1-3.jpg",
        ],
        {
            Filename("TalesOfHayvenCelestia1.epub"): None,
            Filename("TalesOfHayvenCelestia1.mobi"): None,
            Filename("TalesOfHayvenCelestia1.pdf"): None,
        },
        "ebook",
        parent_id=ProductId("tohc1"),
    ),
    Product(
        "Tales of Hayven Celestia 1 − audiobook",
        "Tales of Hayven Celestia 1 (audiobook, short-stories sci-fi anthology)",
        """
            <p>19 hours, 58 minutes</p>
            <p>Voiced by the amazing Piers Ryman</p>
            <p>Digital download is a .zip of DRM-free .mp3 files</p>
            """,
        "/shop/books/tales-of-hayven-celestia-1/audiobook",
        ProductId("tohc1-audiobook"),
        -1,
        27.77,
        ["/static/images/products/tales-of-hayven-celestia-1-1.jpg"],
        {Filename("TalesOfHayvenCelestia1.zip"): None},
        "audiobook",
        parent_id=ProductId("tohc1"),
    ),
    Product(
        "Tales of Hayven Celestia 2",
        "Tales of Hayven Celestia 2",
        """
            <p>
                The universe is an uncaring place … save for the people who inhabit it. They will find friends among the 
                stars who face perils both known and unknown, tackle impossible ship-wide casualties, prove themselves 
                capable against all odds—and above all, find out the truth of who they really are.
            </p>
            <p>
                SciFi / Short Stories
            </p>
            """,
        "/shop/books/tales-of-hayven-celestia-2",
        ProductId("tohc2"),
        images=["/static/images/products/tales-of-hayven-celestia-2-1.jpg"],
        media="paperback, ebook",
        child_ids=[ProductId("tohc2-paperback"), ProductId("tohc2-ebook")],
    ),
    Product(
        "Tales of Hayven Celestia 2 − paperback",
        "Tales of Hayven Celestia 2 (paperback, short-stories sci-fi anthology)",
        "<p>353 pages, Illustrated</p>",
        "/shop/books/tales-of-hayven-celestia-2/paperback",
        ProductId("tohc2-paperback"),
        TALES_OF_HAYVEN_CELESTIA_2,
        22.99,
        images=[
            "/static/images/products/tales-of-hayven-celestia-2-1.jpg",
            "/static/images/products/tales-of-hayven-celestia-2-5.jpg",
            "/static/images/products/tales-of-hayven-celestia-2-6.jpg",
            "/static/images/products/tales-of-hayven-celestia-2-7.jpg",
        ],
        media="paperback",
        parent_id=ProductId("tohc2"),
    ),
    Product(
        "Tales of Hayven Celestia 2 − ebook",
        "Tales of Hayven Celestia 2 (ebook, short-stories sci-fi anthology)",
        """
            <p>353 pages, Illustrated</p>
            <p>Download includes all three DRM-free versions:</p>
            <ul>
                <li>.epub format</li>
                <li>.mobi format</li>
                <li>.pdf format</li>
            </ul>
            """,
        "/shop/books/tales-of-hayven-celestia-2/ebook",
        ProductId("tohc2-ebook"),
        -1,
        9.99,
        [
            "/static/images/products/tales-of-hayven-celestia-2-1.jpg",
            "/static/images/products/tales-of-hayven-celestia-2-2.jpg",
            "/static/images/products/tales-of-hayven-celestia-2-3.jpg",
            "/static/images/products/tales-of-hayven-celestia-2-4.jpg",
        ],
        {
            Filename("TalesOfHayvenCelestia2.epub"): None,
            Filename("TalesOfHayvenCelestia2.mobi"): None,
            Filename("TalesOfHayvenCelestia2.pdf"): None,
        },
        "ebook",
        parent_id=ProductId("tohc2"),
    ),
    Product(
        "Sparkly HC Lapel Pin",
        "Hayven Celestia, sparkly enamel lapel pin (jewelry)",
        """
            <p>
                Show your Hayven Celestia pride with this sparkly lapel pin featuring the Planetary Acquisitions Inc. 
                corporate logo of a krakun claw gripping an unsuspecting world. The peaceful world behind the golden 
                grids glitters in the light as you move!
            </p>
            """,
        "/shop/apparel/hayven-celestia-pin",
        ProductId("hc-pin"),
        HAYVEN_CELESTIA_PIN,
        13.00,
        [
            "/static/images/products/hayven-celestia-pin-1.jpg",
            "/static/images/products/hayven-celestia-pin-2.jpg",
        ],
        media="jewelry",
    ),
]


def write_inventory(products_table: DynamoDBTable) -> None:
    """Write the inventory to the database"""
    products_table.SECRET_OVERRIDE = True  # type: ignore [attr-defined]
    for product in PRODUCTS:
        product.put(products_table)
    products_table.SECRET_OVERRIDE = False  # type: ignore [attr-defined]
