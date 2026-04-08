from typing import Dict, List
from examprep.models import Topic, TopicStatus

UPSC_TOPICS: List[Dict] = [
    {"name": "Ancient Indian History", "subject": "GS1", "weight": 0.06, "estimated_hours": 40},
    {"name": "Medieval Indian History", "subject": "GS1", "weight": 0.05, "estimated_hours": 30},
    {"name": "Modern Indian History", "subject": "GS1", "weight": 0.08, "estimated_hours": 50},
    {"name": "Indian Art & Culture", "subject": "GS1", "weight": 0.05, "estimated_hours": 25},
    {"name": "World Geography", "subject": "GS1", "weight": 0.06, "estimated_hours": 35},
    {"name": "Indian Geography", "subject": "GS1", "weight": 0.07, "estimated_hours": 40},
    {"name": "Indian Society", "subject": "GS1", "weight": 0.05, "estimated_hours": 20},
    {"name": "Indian Constitution", "subject": "GS2", "weight": 0.09, "estimated_hours": 55},
    {"name": "Governance & Public Policy", "subject": "GS2", "weight": 0.07, "estimated_hours": 35},
    {"name": "International Relations", "subject": "GS2", "weight": 0.06, "estimated_hours": 30},
    {"name": "Social Justice", "subject": "GS2", "weight": 0.05, "estimated_hours": 20},
    {"name": "Indian Economy", "subject": "GS3", "weight": 0.09, "estimated_hours": 50},
    {"name": "Agriculture", "subject": "GS3", "weight": 0.04, "estimated_hours": 20},
    {"name": "Science & Technology", "subject": "GS3", "weight": 0.06, "estimated_hours": 30},
    {"name": "Environment & Ecology", "subject": "GS3", "weight": 0.05, "estimated_hours": 25},
    {"name": "Internal Security", "subject": "GS3", "weight": 0.04, "estimated_hours": 20},
    {"name": "Ethics & Integrity", "subject": "GS4", "weight": 0.08, "estimated_hours": 35},
    {"name": "Comprehension & Reasoning", "subject": "CSAT", "weight": 0.05, "estimated_hours": 20},
    {"name": "Basic Numeracy", "subject": "CSAT", "weight": 0.05, "estimated_hours": 20},
]

SSC_CGL_TOPICS: List[Dict] = [
    {"name": "Number System", "subject": "Quantitative", "weight": 0.08, "estimated_hours": 20},
    {"name": "Algebra", "subject": "Quantitative", "weight": 0.07, "estimated_hours": 18},
    {"name": "Geometry", "subject": "Quantitative", "weight": 0.08, "estimated_hours": 22},
    {"name": "Trigonometry", "subject": "Quantitative", "weight": 0.07, "estimated_hours": 18},
    {"name": "Data Interpretation", "subject": "Quantitative", "weight": 0.07, "estimated_hours": 15},
    {"name": "Profit & Loss", "subject": "Quantitative", "weight": 0.05, "estimated_hours": 12},
    {"name": "Time & Work", "subject": "Quantitative", "weight": 0.05, "estimated_hours": 12},
    {"name": "English Grammar", "subject": "English", "weight": 0.08, "estimated_hours": 20},
    {"name": "Vocabulary", "subject": "English", "weight": 0.06, "estimated_hours": 15},
    {"name": "Reading Comprehension", "subject": "English", "weight": 0.07, "estimated_hours": 18},
    {"name": "Analogies & Series", "subject": "Reasoning", "weight": 0.07, "estimated_hours": 15},
    {"name": "Coding-Decoding", "subject": "Reasoning", "weight": 0.06, "estimated_hours": 12},
    {"name": "Syllogism", "subject": "Reasoning", "weight": 0.05, "estimated_hours": 10},
    {"name": "History & Polity", "subject": "General Awareness", "weight": 0.07, "estimated_hours": 20},
    {"name": "Current Affairs", "subject": "General Awareness", "weight": 0.08, "estimated_hours": 15},
]

NEET_TOPICS: List[Dict] = [
    {"name": "Cell Biology", "subject": "Biology", "weight": 0.08, "estimated_hours": 30},
    {"name": "Genetics & Evolution", "subject": "Biology", "weight": 0.09, "estimated_hours": 35},
    {"name": "Human Physiology", "subject": "Biology", "weight": 0.10, "estimated_hours": 40},
    {"name": "Plant Physiology", "subject": "Biology", "weight": 0.07, "estimated_hours": 25},
    {"name": "Ecology", "subject": "Biology", "weight": 0.06, "estimated_hours": 20},
    {"name": "Diversity of Life", "subject": "Biology", "weight": 0.05, "estimated_hours": 20},
    {"name": "Thermodynamics", "subject": "Physics", "weight": 0.07, "estimated_hours": 25},
    {"name": "Mechanics", "subject": "Physics", "weight": 0.08, "estimated_hours": 30},
    {"name": "Electrostatics", "subject": "Physics", "weight": 0.07, "estimated_hours": 25},
    {"name": "Optics", "subject": "Physics", "weight": 0.06, "estimated_hours": 20},
    {"name": "Modern Physics", "subject": "Physics", "weight": 0.05, "estimated_hours": 18},
    {"name": "Organic Chemistry", "subject": "Chemistry", "weight": 0.09, "estimated_hours": 35},
    {"name": "Physical Chemistry", "subject": "Chemistry", "weight": 0.08, "estimated_hours": 30},
    {"name": "Inorganic Chemistry", "subject": "Chemistry", "weight": 0.05, "estimated_hours": 20},
]

EXAM_CURRICULA: Dict[str, List[Dict]] = {
    "upsc":    UPSC_TOPICS,
    "ssc_cgl": SSC_CGL_TOPICS,
    "neet":    NEET_TOPICS,
    "jee":     NEET_TOPICS,
    "psc":     UPSC_TOPICS,
}


def get_topics_for_exam(exam: str) -> List[Topic]:
    raw = EXAM_CURRICULA.get(exam, UPSC_TOPICS)
    return [
        Topic(
            name=t["name"],
            subject=t["subject"],
            weight=t["weight"],
            estimated_hours=t["estimated_hours"],
            status=TopicStatus.NOT_STARTED,
            hours_spent=0.0,
            priority=round(t["weight"] * 10),
        )
        for t in raw
    ]