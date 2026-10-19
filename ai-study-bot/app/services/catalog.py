"""Original educational starter curriculum, authored for this project.

Exam practice examples are intentionally in English; instruction and feedback
are bilingual. These materials are not official examination questions.
"""

from dataclasses import dataclass


@dataclass
class LessonSpec:
    subject: str
    topic: str
    level: str | None
    title: str
    uz: str
    en: str
    audio: str | None = None
    premium: bool = False

    @property
    def code(self):
        return f"{self.subject}-{self.level or 'all'}-{self.topic}"


@dataclass
class QuestionSpec:
    subject: str
    topic: str
    level: str | None
    prompt: str
    options: list[str]
    correct: int
    explanation_en: str
    explanation_uz: str
    difficulty: int = 1
    premium: bool = False


SUBJECTS = {
    "ielts": ("IELTS", "IELTS"),
    "cefr": ("CEFR Multi-Level", "CEFR Multi-Level"),
    "sat_math": ("SAT Matematika", "SAT Math"),
    "sat_rw": ("SAT O‘qish va yozish", "SAT Reading and Writing"),
}

IELTS_READING = (
    "A town converted an unused railway building into a study centre. Before the conversion, "
    "students travelled forty minutes to the nearest public library. The new centre lends laptops "
    "and remains open until nine in the evening. A survey found that evening attendance rose after "
    "quiet rooms were introduced. The survey did not measure examination results, so the manager "
    "warned against claiming that the centre had improved grades."
)

CEFR_READING = {
    "A1": (
        "Mina is a student. She lives near her school. She walks to class every morning. On Saturday she reads at home.",
        [
            (
                "How does Mina get to class?",
                ["On foot", "By bus", "By car", "By train"],
                0,
                "She walks to class.",
            ),
            (
                "Where does Mina read on Saturday?",
                ["At school", "At home", "On a train", "In a shop"],
                1,
                "The text says she reads at home.",
            ),
            (
                "What is Mina?",
                ["A driver", "A doctor", "A student", "A manager"],
                2,
                "The first sentence identifies her as a student.",
            ),
        ],
    ),
    "A2": (
        "Jasur joined a weekend cooking class because he wanted to make healthy lunches. The first lesson began at ten, but he arrived fifteen minutes early. He made vegetable soup and took some home for his sister.",
        [
            (
                "Why did Jasur join the class?",
                [
                    "To teach his sister",
                    "To prepare healthy lunches",
                    "To open a restaurant",
                    "To sell vegetables",
                ],
                1,
                "His stated goal was to make healthy lunches.",
            ),
            (
                "When did Jasur arrive?",
                ["10:15", "10:00", "9:45", "9:15"],
                2,
                "Fifteen minutes before ten is 9:45.",
            ),
            (
                "Who was the soup taken home for?",
                ["His sister", "His teacher", "His neighbour", "His father"],
                0,
                "He took some home for his sister.",
            ),
        ],
    ),
    "B1": (
        "A school tested a bicycle-sharing scheme for six weeks. Students liked the low cost, although some struggled to find a bicycle after afternoon classes. The organisers decided to move more bicycles to the school at lunchtime rather than increase membership fees.",
        [
            (
                "What problem did students report?",
                [
                    "High membership fees",
                    "Few bicycles in the afternoon",
                    "Unsafe roads",
                    "Long registration forms",
                ],
                1,
                "Availability after afternoon classes was the problem.",
            ),
            (
                "How did organisers respond?",
                [
                    "Closed the scheme",
                    "Increased fees",
                    "Moved bicycles at lunchtime",
                    "Shortened classes",
                ],
                2,
                "They redistributed bicycles at lunchtime.",
            ),
            (
                "Which statement is supported?",
                [
                    "The scheme was free",
                    "The trial lasted six weeks",
                    "Every student owned a bicycle",
                    "Fees were doubled",
                ],
                1,
                "The first sentence gives the six-week trial length.",
            ),
        ],
    ),
    "B2": (
        "A museum replaced several printed labels with digital screens. Visitors spent longer at the interactive exhibits, but interviews suggested that the screens sometimes distracted them from the objects. The curator proposed retaining printed summaries alongside the screens so that visitors could choose their preferred format.",
        [
            (
                "What tension does the passage describe?",
                [
                    "Engagement versus distraction",
                    "Cost versus profit",
                    "Security versus access",
                    "Age versus experience",
                ],
                0,
                "Screens increased interaction but could divert attention from objects.",
            ),
            (
                "What did the curator propose?",
                [
                    "Remove all labels",
                    "Use only screens",
                    "Offer both formats",
                    "Shorten opening hours",
                ],
                2,
                "Printed summaries would remain alongside screens.",
            ),
            (
                "What can be inferred about visitors?",
                [
                    "All disliked screens",
                    "Preferences may differ",
                    "They refused interviews",
                    "They visited less often",
                ],
                1,
                "Offering a choice acknowledges differing format preferences.",
            ),
        ],
    ),
    "C1": (
        "Advocates of urban tree planting often cite lower surface temperatures as evidence of success. Yet a programme measured only on the number of trees planted may overlook survival rates and uneven distribution. Evaluating long-term canopy cover by neighbourhood would provide a more revealing measure of both environmental benefit and equity.",
        [
            (
                "What is the author's central criticism?",
                [
                    "Trees never reduce heat",
                    "Planting counts are an incomplete measure",
                    "Neighbourhood data are irrelevant",
                    "Survival cannot be measured",
                ],
                1,
                "Counts can miss survival and distribution, so they do not fully capture impact.",
            ),
            (
                "Why measure canopy cover by neighbourhood?",
                [
                    "To avoid long-term data",
                    "To count purchases",
                    "To assess benefit and equity",
                    "To remove mature trees",
                ],
                2,
                "The proposed measure captures environmental benefit and its distribution.",
            ),
            (
                "The word 'revealing' most nearly means:",
                ["Informative", "Secretive", "Decorative", "Accidental"],
                0,
                "A revealing measure provides useful insight.",
            ),
        ],
    ),
}

GRAMMAR = {
    "A1": [
        (
            "She ___ a student.",
            ["am", "is", "are", "be"],
            1,
            "Use 'is' with she.",
            "She bilan is ishlatiladi.",
        ),
        (
            "I have ___ apple.",
            ["a", "an", "the a", "two"],
            1,
            "Use 'an' before a vowel sound.",
            "Unli tovushdan oldin an ishlatiladi.",
        ),
        (
            "They ___ football every Friday.",
            ["plays", "playing", "play", "is play"],
            2,
            "Plural subjects use the base form in the present simple.",
            "Ko‘plik ega bilan Present Simple asosiy shakl ishlatiladi.",
        ),
    ],
    "A2": [
        (
            "We ___ a film yesterday.",
            ["watch", "watched", "watching", "watches"],
            1,
            "Yesterday requires the past simple.",
            "Yesterday Past Simple zamonini talab qiladi.",
        ),
        (
            "This book is ___ than that one.",
            ["cheap", "cheapest", "cheaper", "more cheap than"],
            2,
            "The comparative of cheap is cheaper.",
            "Cheap ning qiyosiy darajasi cheaper.",
        ),
        (
            "There isn't ___ milk left.",
            ["many", "some a", "any", "a few"],
            2,
            "Any is used in this negative statement with uncountable milk.",
            "Inkor gapda sanalmaydigan milk bilan any ishlatiladi.",
        ),
    ],
    "B1": [
        (
            "If it rains, we ___ indoors.",
            ["stayed", "will stay", "would stayed", "staying"],
            1,
            "First conditional: if + present, will + base verb.",
            "Birinchi shart: if + hozirgi zamon, will + fe’l.",
        ),
        (
            "I have lived here ___ 2021.",
            ["for", "during", "since", "by"],
            2,
            "Since introduces a starting point in time.",
            "Since vaqtning boshlanish nuqtasini bildiradi.",
        ),
        (
            "The bridge ___ last year.",
            ["built", "was built", "has build", "is building"],
            1,
            "Past passive: was/were + past participle.",
            "O‘tgan zamon majhul nisbat: was/were + past participle.",
        ),
    ],
    "B2": [
        (
            "If I had more time, I ___ another language.",
            ["learn", "will learn", "would learn", "had learn"],
            2,
            "Second conditional describes a hypothetical present situation.",
            "Ikkinchi shart hozirgi faraziy holatni bildiradi.",
        ),
        (
            "Despite ___ tired, she finished the report.",
            ["be", "being", "was", "she being"],
            1,
            "Despite is followed by a noun or gerund.",
            "Despite dan keyin ot yoki gerund keladi.",
        ),
        (
            "He suggested that she ___ earlier.",
            ["arrives", "arrive", "arriving", "has arrive"],
            1,
            "The mandative subjunctive uses the base verb after suggested that.",
            "Suggested that dan keyin subjunctive fe’lning asosiy shaklini oladi.",
        ),
    ],
    "C1": [
        (
            "Rarely ___ such a convincing argument.",
            ["I heard", "have I heard", "I have hear", "heard I have"],
            1,
            "Fronted negative adverbials trigger subject–auxiliary inversion.",
            "Oldinga chiqarilgan inkor ravishdan keyin yordamchi fe’l egadan oldin keladi.",
        ),
        (
            "Had they checked the figures, they ___ the error.",
            ["will find", "would have found", "would find yesterday", "have found"],
            1,
            "Inverted third conditional: had + subject + participle; would have + participle.",
            "Inversiyali uchinchi shart natijasi would have + past participle bilan beriladi.",
        ),
        (
            "The evidence, ___ limited, supports further investigation.",
            ["albeit", "despite of", "whereas of", "unless of"],
            0,
            "Albeit means although and can introduce a reduced concessive phrase.",
            "Albeit garchi degani bo‘lib, qisqartirilgan to‘siqsiz ergash birikmani kiritadi.",
        ),
    ],
}

VOCABULARY = {
    "A1": [
        ("A person who teaches is a ___.", ["teacher", "kitchen", "window", "Tuesday"], 0),
        ("The opposite of 'hot' is:", ["tall", "cold", "fast", "young"], 1),
        ("You buy bread at a ___.", ["station", "hospital", "bakery", "river"], 2),
    ],
    "A2": [
        ("Please ___ the light; it is dark.", ["turn on", "look after", "give up", "take off"], 0),
        ("A journey by plane is a ___.", ["recipe", "flight", "receipt", "shelf"], 1),
        (
            "'Affordable' describes something:",
            ["Very noisy", "Easy to carry", "Not too expensive", "Impossible to find"],
            2,
        ),
    ],
    "B1": [
        (
            "To 'postpone' a meeting means to:",
            ["Hold it earlier", "Cancel it forever", "Arrange it for later", "Attend it twice"],
            2,
        ),
        ("A 'reliable' person is someone you can:", ["Trust", "Measure", "Borrow", "Repair"], 0),
        ("The new policy aims to ___ waste.", ["reduce", "invent", "persuade", "arrive"], 0),
    ],
    "B2": [
        (
            "A 'feasible' plan is:",
            ["Impractical", "Possible to carry out", "Already illegal", "Entirely accidental"],
            1,
        ),
        (
            "The results were 'inconclusive', so they:",
            [
                "Proved the claim",
                "Ended the debate",
                "Did not settle the question",
                "Were never collected",
            ],
            2,
        ),
        (
            "To 'allocate' resources means to:",
            [
                "Distribute them for a purpose",
                "Destroy them",
                "Hide them permanently",
                "Count them incorrectly",
            ],
            0,
        ),
    ],
    "C1": [
        (
            "A 'tentative' conclusion is:",
            ["Final and certain", "Provisional", "Unrelated", "Compulsory"],
            1,
        ),
        (
            "To 'corroborate' a claim means to:",
            [
                "Provide supporting evidence",
                "Express doubt without evidence",
                "Translate it",
                "Repeat it more loudly",
            ],
            0,
        ),
        (
            "A 'salient' feature is:",
            ["Unimportant", "Prominent", "Invisible", "Temporary by definition"],
            1,
        ),
    ],
}


def lessons():
    result = []
    descriptions = {
        "reading": (
            "Asosiy g‘oya, dalil va xulosani ajrating. Savolga matndagi dalil bilan javob bering.",
            "Identify the main idea, evidence and inference. Support answers with the passage.",
        ),
        "grammar": (
            "Zamon, gap tuzilishi va fe’l shakllarini kontekstda mashq qiling. Xatolar izohini o‘qing.",
            "Practise tense, sentence structure and verb forms in context. Review each explanation.",
        ),
        "vocabulary": (
            "So‘z ma’nosini kontekstdan toping, so‘ng uni yangi gapda ishlating.",
            "Infer meaning from context, then use each word in a new sentence.",
        ),
    }
    for level, (passage, _) in CEFR_READING.items():
        for topic, (uz, en) in descriptions.items():
            body = f"\n\n{passage}" if topic == "reading" else ""
            result.append(
                LessonSpec("cefr", topic, level, f"CEFR {level} · {topic}", uz + body, en + body)
            )
        writing_tasks = {
            "A1": "Write 40–60 words introducing yourself, your daily routine and one hobby.",
            "A2": "Write an 80–100 word invitation to a friend. Give the place, time and planned activities.",
            "B1": "Write a 120–160 word email to a community centre suggesting a new weekend class and explaining why it is useful.",
            "B2": "Write a 180–220 word essay discussing the advantages and disadvantages of remote study. Give examples and a conclusion.",
            "C1": "Write a 250–300 word proposal for a school to improve access to independent study. Compare two options, consider constraints and justify a recommendation.",
        }
        result.append(
            LessonSpec(
                "cefr",
                "writing",
                level,
                f"CEFR {level} · Writing",
                "Topshiriq bo‘yicha matn yozing:\n" + writing_tasks[level],
                writing_tasks[level],
            )
        )
        speaking = f"Describe a learning experience at CEFR {level} level. Explain what you learned, what was difficult, and what you would do differently."
        result.append(
            LessonSpec(
                "cefr",
                "speaking",
                level,
                f"CEFR {level} · Speaking",
                "Og‘zaki yoki yozma javob bering:\n" + speaking,
                speaking,
            )
        )
        audio = f"Hello, this is a message from the learning centre. The {level} English workshop will take place on Saturday at ten in room twelve. Please bring a notebook. The workshop costs nothing. You need to register by Thursday."
        listening = "Listen and answer in English: 1. On which day is the workshop? 2. Which room is it in? 3. What is the registration deadline?"
        result.append(
            LessonSpec(
                "cefr",
                "listening",
                level,
                f"CEFR {level} · Listening",
                "Audioni tinglab, savollarga javob bering.\n" + listening,
                listening,
                audio,
            )
        )
    for topic, (uz, en) in descriptions.items():
        body = f"\n\n{IELTS_READING}" if topic == "reading" else ""
        result.append(LessonSpec("ielts", topic, None, f"IELTS · {topic}", uz + body, en + body))
    tasks = {
        "writing1": "Write at least 150 words summarising these original data. Library visits (thousands): 2015 — Central 40, Riverside 20; 2020 — Central 45, Riverside 35; 2025 — Central 50, Riverside 55. Compare trends and key differences; do not invent causes.",
        "writing2": "Write at least 250 words. Some people believe schools should devote more time to practical life skills, while others prioritise traditional academic subjects. Discuss both views and give your own opinion.",
        "speaking1": "Answer these short questions: What subject do you enjoy most? When do you usually study? Do you prefer studying alone or with others? Explain why.",
        "speaking2": "Take one minute to prepare, then speak for 1–2 minutes: Describe a skill you learned outside school. Say what it was, how you learned it, what was difficult, and why it matters to you.",
        "speaking3": "Discuss: How should schools decide which skills to teach? Can technology replace a teacher? Who should fund adult education? Give reasons and examples.",
    }
    for topic, task in tasks.items():
        result.append(
            LessonSpec(
                "ielts", topic, None, f"IELTS · {topic}", "Original topshiriq:\n" + task, task
            )
        )
    audio = "Welcome to the community study centre. Our evening reading group has moved from Tuesday to Wednesday. It starts at half past six and ends at eight. The meeting is in the garden room, not the main hall. Please email your name by Monday. Membership is free, but bring your own copy of the book."
    listening = "Listen and answer: 1. What day does the group meet now? 2. What time does it start? 3. Which room is used? 4. By when should you email your name?"
    result.append(
        LessonSpec(
            "ielts",
            "listening",
            None,
            "IELTS · Listening",
            "Audioni tinglang.\n" + listening,
            listening,
            audio,
        )
    )
    sat_topics = {
        "sat_math": {
            "algebra": (
                "Chiziqli tenglamalar va tizimlar",
                "Linear equations and systems",
                "Isolate the variable by applying the same operation to both sides. For systems, substitution and elimination must preserve both equations.",
            ),
            "advanced_math": (
                "Kvadratlar va darajalar",
                "Quadratics and exponents",
                "Factor quadratics when possible. For x² = a, check both positive and negative roots unless a sign is specified. Apply exponent rules to a common base.",
            ),
            "data_analysis": (
                "Foiz, o‘rtacha va ehtimollik",
                "Percentages, averages and probability",
                "Percent change = change/original × 100. The mean is sum/count; probability is favourable outcomes/total equally likely outcomes.",
            ),
            "geometry": (
                "Geometriya va trigonometriya",
                "Geometry and trigonometry",
                "Triangle area = base × perpendicular height / 2. In a right triangle, sin θ = opposite/hypotenuse and cos θ = adjacent/hypotenuse. Check units.",
            ),
        },
        "sat_rw": {
            "vocabulary_context": (
                "Kontekst bo‘yicha so‘z ma’nosi",
                "Vocabulary in Context",
                "Use surrounding evidence to select the meaning that fits the sentence, rather than a word's most familiar meaning.",
            ),
            "grammar": (
                "Standart ingliz tili",
                "Standard English Conventions",
                "Check subject–verb agreement, sentence boundaries and punctuation. A semicolon joins two independent clauses.",
            ),
            "transitions": (
                "Mantiqiy bog‘lanishlar",
                "Transitions",
                "Determine whether ideas contrast, add, illustrate, or show cause and effect before choosing a transition.",
            ),
            "main_ideas": (
                "Markaziy fikr va tafsilot",
                "Central Ideas and Details",
                "A main idea covers the whole passage; avoid an option that mentions only a minor detail or goes beyond the evidence.",
            ),
            "inference": (
                "Dalil asosida xulosa",
                "Inference",
                "Choose the conclusion most strongly supported by the stated evidence. Avoid absolute claims that the passage cannot justify.",
            ),
            "rhetorical_synthesis": (
                "Maqsadga mos umumlashtirish",
                "Rhetorical Synthesis",
                "Identify the student's stated writing goal, then select only the notes that serve that goal. Accuracy alone is insufficient if an option misses the goal.",
            ),
        },
    }
    for subject, topics in sat_topics.items():
        for topic, (uz, en, body) in topics.items():
            result.append(LessonSpec(subject, topic, None, en, f"{uz}\n\n{body}", body))
    return result


def questions():
    result = []
    for level, (passage, reading) in CEFR_READING.items():
        for i, (prompt, options, correct, explanation) in enumerate(reading):
            result.append(
                QuestionSpec(
                    "cefr",
                    "reading",
                    level,
                    passage + "\n\n" + prompt,
                    options,
                    correct,
                    explanation,
                    "Matndagi dalil: " + explanation,
                    i + 1,
                )
            )
        for topic, source in (("grammar", GRAMMAR[level]), ("vocabulary", VOCABULARY[level])):
            for i, row in enumerate(source):
                prompt, options, correct = row[:3]
                en = (
                    row[3]
                    if len(row) > 3
                    else f"The correct expression is '{options[correct]}', which fits this context."
                )
                uz = row[4] if len(row) > 4 else f"Kontekstga mos javob: {options[correct]}."
                result.append(
                    QuestionSpec("cefr", topic, level, prompt, options, correct, en, uz, i + 1)
                )
    ielts_reading = [
        (
            "What was the building used for previously?",
            ["Railway activities", "A hospital", "A hotel", "A farm"],
            0,
            "It was an unused railway building.",
        ),
        (
            "Why is a claim about improved grades unsupported?",
            [
                "No students attended",
                "The survey did not measure exam results",
                "All rooms were closed",
                "The manager rejected all surveys",
            ],
            1,
            "Attendance data alone cannot establish an effect on examination results.",
        ),
        (
            "What changed before evening attendance rose?",
            [
                "Fees doubled",
                "Laptops were removed",
                "Quiet rooms were introduced",
                "Opening hours ended at six",
            ],
            2,
            "The passage links the rise in attendance to the introduction of quiet rooms, without proving causality.",
        ),
        (
            "When does the centre close?",
            ["6 pm", "7 pm", "8 pm", "9 pm"],
            3,
            "It remains open until nine in the evening.",
        ),
        (
            "What is the manager's attitude toward the evidence?",
            [
                "Cautious",
                "Dismissive of all learning",
                "Certain grades improved",
                "Uninterested in attendance",
            ],
            0,
            "The manager avoids extending the findings beyond what was measured.",
        ),
    ]
    for i, (prompt, options, correct, explanation) in enumerate(ielts_reading):
        result.append(
            QuestionSpec(
                "ielts",
                "reading",
                None,
                IELTS_READING + "\n\n" + prompt,
                options,
                correct,
                explanation,
                "Matndagi dalil: " + explanation,
                i % 3 + 1,
            )
        )
    for level in ("B1", "B2", "C1"):
        for topic, source in (("grammar", GRAMMAR[level]), ("vocabulary", VOCABULARY[level])):
            for i, row in enumerate(source):
                prompt, options, correct = row[:3]
                en = row[3] if len(row) > 3 else f"'{options[correct]}' matches the context."
                uz = row[4] if len(row) > 4 else f"Kontekstga mos javob: {options[correct]}."
                result.append(
                    QuestionSpec(
                        "ielts",
                        topic,
                        None,
                        prompt,
                        options,
                        correct,
                        en,
                        uz,
                        ("B1", "B2", "C1").index(level) + 1,
                        premium=(level == "C1" and i == 2),
                    )
                )
    for i in range(6):
        a, b, x = i + 2, i + 3, i + 1
        c = a * x + b
        result.append(
            QuestionSpec(
                "sat_math",
                "algebra",
                None,
                f"If {a}x + {b} = {c}, what is x?",
                [str(x + 1), str(x), str(x + 2), str(x - 1)],
                1,
                f"Subtract {b} to get {a}x = {c - b}, then divide by {a}: x = {x}.",
                f"Ikki tomondan {b} ni ayiring: {a}x = {c - b}. {a} ga bo‘ling: x = {x}.",
                i // 2 + 1,
            )
        )
        root = i + 2
        result.append(
            QuestionSpec(
                "sat_math",
                "advanced_math",
                None,
                f"For x > 0, x² = {root * root}. What is x + 3?",
                [str(root), str(root + 3), str(root * root + 3), str(3 - root)],
                1,
                f"The positive square root is {root}, so x + 3 = {root + 3}.",
                f"Musbat kvadrat ildiz {root}, shuning uchun x + 3 = {root + 3}.",
                i // 2 + 1,
            )
        )
        original = (i + 2) * 20
        increase = original // 4
        result.append(
            QuestionSpec(
                "sat_math",
                "data_analysis",
                None,
                f"A club grows from {original} to {original + increase} members. What is the percentage increase?",
                ["20%", "25%", "50%", "125%"],
                1,
                f"Increase = {increase}; percentage = {increase}/{original} × 100 = 25%.",
                f"O‘sish {increase}. Foiz = {increase}/{original} × 100 = 25%.",
                i // 2 + 1,
            )
        )
        base, height = i + 4, 6
        result.append(
            QuestionSpec(
                "sat_math",
                "geometry",
                None,
                f"A triangle has base {base} cm and perpendicular height {height} cm. What is its area in cm²?",
                [
                    str(base * height),
                    str(base + height),
                    str(base * height // 2),
                    str(2 * (base + height)),
                ],
                2,
                f"Area = base × height / 2 = {base} × {height} / 2 = {base * height // 2} cm².",
                f"Yuza = asos × balandlik / 2 = {base * height // 2} cm².",
                i // 2 + 1,
            )
        )
    result.append(
        QuestionSpec(
            "sat_math",
            "geometry",
            None,
            "In a right triangle, the side opposite angle θ is 3 and the hypotenuse is 5. What is sin θ?",
            ["3/5", "4/5", "5/3", "5/4"],
            0,
            "sin θ = opposite/hypotenuse = 3/5.",
            "sin θ = qarshi katet/gipotenuza = 3/5.",
            3,
        )
    )
    rw = {
        "vocabulary_context": [
            (
                "The scientist's cautious language reflected a tentative conclusion. 'Tentative' most nearly means:",
                ["Provisional", "Permanent", "Unrelated", "Aggressive"],
                0,
                "Cautious language signals that the conclusion is provisional.",
            ),
            (
                "The editor condensed the article from 900 words to 400. 'Condensed' means:",
                ["Translated", "Shortened", "Rejected", "Illustrated"],
                1,
                "The reduced word count shows the article was shortened.",
            ),
            (
                "The second experiment corroborated the first finding by producing similar results. 'Corroborated' means:",
                ["Contradicted", "Concealed", "Supported", "Delayed"],
                2,
                "Similar results provide support for the initial finding.",
            ),
        ],
        "grammar": [
            (
                "The collection of maps ___ in the archive.",
                ["are", "is", "were", "have been"],
                1,
                "The head of the subject is the singular noun collection.",
            ),
            (
                "Choose the correctly punctuated sentence.",
                [
                    "The trial ended, the data remained uncertain.",
                    "The trial ended; the data remained uncertain.",
                    "The trial, ended the data remained uncertain.",
                    "The trial ended the data, remained uncertain.",
                ],
                1,
                "A semicolon can join these two independent clauses.",
            ),
            (
                "Neither the assistants nor the researcher ___ available today.",
                ["are", "were", "is", "have been"],
                2,
                "With neither/nor, agreement follows the nearer subject, researcher.",
            ),
        ],
        "transitions": [
            (
                "The first prototype used much energy. ___, the revised model required very little. Choose the contrast transition.",
                ["Similarly", "However", "For example", "Therefore"],
                1,
                "However contrasts high and low energy use.",
            ),
            (
                "The path was flooded. ___, the group chose another route.",
                ["Consequently", "Nevertheless", "Likewise", "For instance"],
                0,
                "The route change is a consequence of flooding.",
            ),
            (
                "The tool is inexpensive. ___, it is easy to repair.",
                ["In contrast", "Nonetheless", "Moreover", "Instead"],
                2,
                "Moreover adds another advantage.",
            ),
        ],
        "main_ideas": [
            (
                "A small library lent seeds in spring. Gardeners returned seeds after harvest, allowing more residents to participate the next year. What is the main idea?",
                [
                    "A sharing programme can sustain itself through contributions",
                    "All seeds grow in spring",
                    "Libraries should stop lending books",
                    "Harvests are always large",
                ],
                0,
                "Returning seeds replenishes the shared supply and enables future participation.",
            ),
            (
                "Engineers studied a bird's folding wing and used a similar joint in a compact drone. The design reduced storage space without changing flight range. What is the main idea?",
                [
                    "Birds are smaller than drones",
                    "A natural structure inspired a practical design improvement",
                    "Flight range doubled",
                    "Storage is never important",
                ],
                1,
                "The passage focuses on applying a biological structure to engineering.",
            ),
            (
                "A town tested two bus timetables. More passengers used the timetable with frequent short trips than the one with fewer long routes. Which statement best summarises the result?",
                [
                    "All routes should be removed",
                    "Long routes were faster",
                    "The more frequent service attracted more riders",
                    "Passengers never travelled far",
                ],
                2,
                "Only the difference in ridership across the two schedules is established.",
            ),
        ],
        "inference": [
            (
                "A plant grew toward a window. After its pot was rotated, new growth curved toward the window again. Which inference is best supported?",
                [
                    "The growth responds to light direction",
                    "The plant cannot survive indoors",
                    "Rotation always increases height",
                    "All plants grow at the same speed",
                ],
                0,
                "Repeated growth toward the light source supports a directional response.",
            ),
            (
                "A cafe sold more hot tea on colder days during a month. What can be inferred?",
                [
                    "Cold weather was associated with higher tea sales",
                    "Weather alone caused every purchase",
                    "Coffee was never sold",
                    "Prices must have fallen",
                ],
                0,
                "The observed association does not by itself establish a sole cause.",
            ),
            (
                "Two fragments from a vessel fit together and have the same glaze. Archaeologists found them in adjacent rooms. Which inference is best supported?",
                [
                    "The rooms were built on the same day",
                    "The fragments may come from the same vessel",
                    "Every vessel had this glaze",
                    "The vessel was imported",
                ],
                1,
                "Fit and matching glaze support a shared vessel, without proving origin or dates.",
            ),
        ],
        "rhetorical_synthesis": [
            (
                "Notes: A study centre opened in 2022. It has 40 desks. It offers evening access. Goal: highlight a benefit for people who work during the day. Which sentence meets the goal?",
                [
                    "The centre opened in 2022",
                    "There are 40 desks",
                    "Evening access lets daytime workers use the centre after work",
                    "A centre is a building",
                ],
                2,
                "Only the third option links a relevant feature to the specified audience.",
            ),
            (
                "Notes: Method A uses 3 litres of water; Method B uses 8 litres; both clean the same number of items. Goal: compare water efficiency. Choose the best sentence.",
                [
                    "Both methods clean items",
                    "Method A uses 5 fewer litres than B for the same output",
                    "Method B is the only safe method",
                    "Water is a liquid",
                ],
                1,
                "The comparison quantifies lower water use for equal output without adding unsupported claims.",
            ),
            (
                "Notes: A poet published a first collection in 2018; a second in 2023; the second uses longer narrative poems. Goal: describe a change in style. Choose the best sentence.",
                [
                    "The poet published books",
                    "The first collection appeared in 2018",
                    "The 2023 collection shifts toward longer narrative poems",
                    "The poet won an award",
                ],
                2,
                "The third option describes the documented stylistic change.",
            ),
        ],
    }
    for topic, rows in rw.items():
        for i, (prompt, options, correct, explanation) in enumerate(rows):
            result.append(
                QuestionSpec(
                    "sat_rw",
                    topic,
                    None,
                    prompt,
                    options,
                    correct,
                    explanation,
                    "Izoh: " + explanation,
                    i + 1,
                )
            )
    return result
