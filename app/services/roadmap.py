import json
import re
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.roadmap import RoadmapMilestone, RoadmapGenerateRequest
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI




def _get_roadmap_llm():
    provider = settings.roadmap_llm_provider.lower().strip()

    if provider == "nvidia":
        if not settings.nvidia_api_key:
            raise ValueError(
                "NVIDIA_API_KEY is missing from the environment"
            )

        return ChatOpenAI(
            model=settings.nvidia_model,
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_api_key,
            temperature=0.3,
        )

    if provider == "ollama":
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.3,
        )

    raise ValueError(
        f"Unsupported roadmap LLM provider: {provider}"
    )




def generate_roadmap(payload: RoadmapGenerateRequest) -> dict:
    llm = _get_roadmap_llm()

    skills = ", ".join(payload.current_skills) or "Not specified"
    background = payload.background or "Not specified"

    prompt = f"""
You are SkillPilot's Career Curriculum Architect and Learning Designer.

Your job is to transform a student's career goal into a complete,
sequenced, practical learning curriculum.

The student may provide only a short goal, such as:
"Give me a roadmap to become a Cloud Engineer."

The student is not expected to know the required skills, topics,
technologies, or learning order. You must determine those yourself.

STUDENT INPUT
Target career: {payload.target_role}
Current skills: {skills}
Background: {background}

If the student has not provided their experience level, assume they are
a beginner. Make reasonable assumptions, and do not invent experience,
qualifications, or preferences for the student.

========================
PHASE 1: CAREER ANALYSIS
========================

Before drafting the roadmap, internally analyze the target career.

Identify:
- Foundational knowledge required before specialized learning.
- Core competencies and technical skills used in the role.
- Common tools, technologies, and workflows.
- Practical activities a learner should be able to perform.
- Important security, reliability, ethical, or cost considerations.
- Projects or evidence that demonstrate practical competence.
- Skills that are essential for entry-level readiness versus optional
  specializations.

Use sound general knowledge. Do not invent certification requirements,
employer requirements, or claims of guaranteed employment.

If the role has several competing platforms, select one reasonable
primary platform for a beginner's path. Explain the choice briefly in
the relevant milestone. Mention alternatives only where useful.

Do not output this analysis separately.

========================
PHASE 2: LEARNING SEQUENCE
========================

Construct a curriculum from prerequisites to practical job readiness.

For every major skill area, determine:
- What the learner needs to know first.
- Which concepts should be taught within this skill area.
- Which exercises help the learner practise those concepts.
- What practical result demonstrates progress.
- How this skill will be used in a later milestone or project.

Order the milestones so the learner is not expected to use a skill
before learning its necessary foundations.

Do not organize the roadmap merely as a list of popular tools.
Organize it as a learning progression.

Create 7 to 10 milestones for a broad career roadmap. Use fewer only
when the target is genuinely narrow; do not omit important competencies
just to meet a milestone count.

========================
PHASE 3: MILESTONE DESIGN
========================

Each milestone must have:

1. A specific title describing the skill area.
2. A meaningful description of the capability the learner will gain.
3. Four to six tasks, unless the skill area genuinely requires a
   different number.
4. A clear relationship to earlier or later milestones.
5. A practical outcome, exercise, or project where appropriate.
For every milestone, explicitly populate:
- topics_to_learn: the specific concepts, techniques, or tools to study.
- completion_criteria: observable checks or deliverables showing the learner
  has achieved the milestone.
- project: an optional practical project, if one fits the milestone.
- prerequisites: relevant earlier milestones or skills, if any.

Do not repeat the task list as topics_to_learn.
Do not use vague completion criteria such as "understand the topic."
Use demonstrable outcomes, such as implementing, testing, explaining,
or documenting a specific capability.


Avoid milestone titles that are too broad, such as "Learn Technology"
or "Advanced Skills".

========================
PHASE 4: TASK DESIGN
========================

Each task must be a small, understandable learning unit.

Write 2 to 4 useful sentences per task. Include:

A. LEARN:
Name the specific concept, subtopic, command, tool, or technique.
Do not use only a broad label.

B. PRACTISE:
Give a concrete exercise, experiment, configuration activity, or
small implementation that the learner can actually attempt.

C. DEMONSTRATE:
State what the learner should produce, explain, test, or show to
demonstrate completion.

D. CONNECTION:
Where helpful, explain how the task prepares the learner for a later
task or milestone.

For example, a weak task is:
"Learn networking."

A stronger task is:
"Study IPv4 addresses, private versus public addresses, and ports.
Use your computer's network tools to inspect its IP configuration,
then explain what an IP address and a port identify. Record your
findings and correctly distinguish an address from a port."

Do not copy this example into unrelated career roadmaps. Create examples
and exercises appropriate to the actual target career.

Avoid vague or non-actionable tasks such as:
- Learn the basics.
- Understand the technology.
- Practice more.
- Explore the tools.
- Build a project.
- Become familiar with the platform.

If a task says "build", "configure", "deploy", "secure", "automate",
or "troubleshoot", explain what to build or change and how the learner
can verify the result.

Keep each task realistic for the learner's assumed level. Do not make
every task a large project.

========================
PHASE 5: PRACTICAL LEARNING
========================

Include hands-on practice throughout the roadmap, not only at the end.

Progress from:
- Small guided exercises.
- Independent practice.
- Combining related skills.
- An integrated portfolio project.
- Explaining, documenting, and troubleshooting the result.

For cloud, infrastructure, or other services that may incur costs:
include safe account practices, cost awareness, and resource cleanup
in relevant tasks. Do not imply that all exercises are free.

For software-related careers, include version control, debugging,
testing, and documentation where relevant.

Do not force these examples into careers where they are not applicable.

========================
PHASE 6: SELF-REVIEW
========================

Before returning the result, review your draft as a strict curriculum
quality reviewer.

Check:
- Are the major essential skill areas represented?
- Are prerequisites taught before dependent skills?
- Does the roadmap begin at the appropriate learner level?
- Does each task name a specific topic and a concrete practice activity?
- Does each task provide an observable completion result?
- Are any tasks vague, repetitive, or too large?
- Does practical work gradually increase in difficulty?
- Does the final project use skills taught earlier?
- Are important safety, security, or cost concerns addressed?
- Are optional advanced topics clearly distinguished from core skills?

If you find a weakness, revise the roadmap before returning it.
Do not include this review or its checklist in the output.

========================
OUTPUT REQUIREMENTS
========================

Return ONLY one valid JSON object. Do not include Markdown fences,
commentary, analysis, or text before or after the JSON.

Use this exact structure:
{{
  "title": "A concise career-specific roadmap title",
  "target_role": "{payload.target_role}",
  "milestones": [
    {{
      "title": "Specific milestone title",
      "description": "The capability the learner should gain",
      "topics_to_learn": [
        "Specific concept or topic",
        "Another specific concept"
      ],
      "tasks": [
        "A specific learning task with practice and a completion result."
      ],
      "project": "A practical project for this milestone, or null",
      "completion_criteria": [
        "An observable result that demonstrates the learner has achieved the milestone"
      ],
      "prerequisites": [
        "A previous milestone or prerequisite skill, or an empty list if none"
      ]
    }}
  ]
}}

Every milestone must include all seven fields shown above.
`topics_to_learn` and `completion_criteria` must each contain
at least one specific, meaningful item.
`tasks` must contain actionable, non-empty strings.
`project` may be null when a separate project is not appropriate.
`prerequisites` may be an empty list when no prerequisite is needed.

Make sure the milestones are ordered from foundational knowledge
toward practical readiness for the target career.


TARGET ROLE REQUIREMENTS

Design the entire roadmap specifically for the student's requested target career:

"{payload.target_role}"

The target career above is authoritative. Do not substitute it with
another occupation, specialization, or trending technology field.

Every milestone, topic, task, and project must directly support
progress toward this target career.

Choose foundations, tools, frameworks, and projects that are relevant
to the requested career. Include AI, GenAI, cloud, or other specialized
topics only when they are genuinely useful for the target role or
explicitly requested by the student.

Before returning the roadmap, verify that the title and all milestones
match the requested target career. If the target is Frontend Developer,
for example, prioritize frontend development skills and projects rather
than an AI engineering curriculum.


For milestones where a project is appropriate, provide a concrete
project deliverable instead of setting "project" to null.

"""

    response = llm.invoke(prompt)
    try:
        raw_output = response.content.strip()

# Remove Markdown code fences if the model includes them.
        raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
        raw_output = re.sub(r"\s*```$", "", raw_output)

        result = json.loads(raw_output)

        # Validate each generated milestone against our Pydantic model.
        milestones = [
            RoadmapMilestone.model_validate(item).model_dump()
            for item in result["milestones"]
        ]

        return {
            "title": result["title"],
            "target_role": payload.target_role,
            "milestones": milestones,
        }

    except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as exc:
        raise ValueError("Roadmap model returned an invalid revised roadmap format") from exc
    

def revise_roadmap(
    current_roadmap: dict,
    instructions: str,
) -> dict:
    llm = _get_roadmap_llm()

    current_roadmap_json = json.dumps(current_roadmap, ensure_ascii=False)

    prompt = f"""
You are SkillPilot's Career Curriculum Architect and Roadmap Editor.

Your task is to improve the student's existing roadmap according to their revision request. Produce a practical, well-sequenced curriculum that matches the student's intended career goal.

EXISTING ROADMAP:
{current_roadmap_json}

STUDENT'S REQUEST:
{instructions}

Interpret brief requests reasonably. For example, if a student says "Make my Cloud Engineer roadmap more detailed," improve its essential skills, prerequisite sequence, specific topics, practical exercises, and completion evidence without requiring the student to enumerate every change.

========================
CRITICAL RULE: IDENTIFY THE REQUESTED CAREER
========================

Before revising, determine whether the student is asking to change the target career.

A career change may be expressed in wording such as:
- "Change my roadmap to Gen AI Engineer."
- "I want to become a Machine Learning Engineer instead."
- "Make this a roadmap for becoming a Cybersecurity Analyst."
- "Replace the Data Engineer roadmap with a Gen AI Engineer roadmap."

If the student explicitly requests a different career:

1. Treat the career named in the student's request as the NEW target role.
2. Set `target_role` to that requested career. Do not retain the old role.
3. Update the roadmap title to clearly reflect the new career.
4. Rebuild or substantially revise the milestones and tasks so they prepare the student for the NEW career.
5. Remove old-career material that is no longer relevant. Retain existing content only when it is genuinely useful to the new career, such as shared programming or database foundations.
6. Do not merely add one milestone about the new career to the old roadmap.
7. Do not interpret the new career as a specialization, additional skill, or side topic of the old career unless the student explicitly says that is what they want.

The existing roadmap is background context, NOT a constraint on the student's new career goal.

For example:

Existing target role: Data Engineer
Student request: "Change this to a Gen AI Engineer roadmap."

Required result:
- `target_role` must be "Gen AI Engineer".
- The title must identify a Gen AI Engineer roadmap.
- The curriculum must be designed for Gen AI Engineering.
- Data engineering topics may remain only when they support the new career.
- The roadmap must not remain primarily a Data Engineer curriculum.

If the student does NOT explicitly request a career change, preserve the existing target role. Do not infer a new career from a request to improve, expand, simplify, or reorganize the roadmap.

If the requested target career is ambiguous, use the student's wording as closely as possible. Do not silently substitute a different occupation.

========================
PHASE 1: AUDIT THE CURRENT ROADMAP
========================

Inspect the existing roadmap for:
- Missing essential competencies for the intended target career.
- Missing prerequisite knowledge.
- Milestones in an unsuitable order.
- Tasks that merely name a skill without teaching steps.
- Tasks without practice or completion evidence.
- Repeated or unnecessary tasks.
- Projects that require skills not taught earlier.
- Missing practical, security, reliability, testing, or cost considerations where relevant.

Do not assume the existing roadmap is correct merely because it exists.

When the target career changes, audit the roadmap against the NEW career rather than the old career.

========================
PHASE 2: APPLY THE REQUEST
========================

Make the changes needed to satisfy the student's instructions.

Preserve useful and relevant content. Add, expand, remove, or reorder milestones when necessary to improve the learning path.

If the request changes the target career, redesign the curriculum around that career. Do not preserve irrelevant old-career milestones just to maintain the original roadmap.

If the request is to make the roadmap comprehensive, ensure it covers major essential skill areas and progresses from foundations to practical job readiness.

If the request is narrowly scoped and does not change the career goal, focus on that change and avoid unnecessary redesign.

========================
PHASE 3: IMPROVE TASK QUALITY
========================


For every milestone, explicitly populate:
- topics_to_learn: the specific concepts, techniques, or tools to study.
- completion_criteria: observable checks or deliverables showing the learner
  has achieved the milestone.
- project: an optional practical project, if one fits the milestone.
- prerequisites: relevant earlier milestones or skills, if any.

Each milestone should contain four to six tasks unless the skill area
genuinely requires a different number.

Do not repeat the task list as topics_to_learn.
Do not use vague completion criteria such as "understand the topic."
Use demonstrable outcomes, such as implementing, testing, explaining,
or documenting a specific capability.

Each task should use 2 to 4 useful sentences to describe:
1. The specific topic, concept, tool, or technique.
2. A concrete exercise or practical activity.
3. A result the learner can produce, explain, or verify.

Replace vague tasks such as "learn the basics", "practice more", "understand the tool", or "build a project" with specific instructions.

Ensure later tasks use skills taught in earlier milestones.

Include practical projects, testing, troubleshooting, and documentation where relevant to the career.

For cloud or infrastructure learning, consider cost, security, and cleanup of resources in relevant tasks.

========================
PHASE 4: SELF-REVIEW
========================

Before returning the revised roadmap, check:
- Did I satisfy the student's actual request?
- If the student requested a career change, does `target_role` exactly reflect the new career?
- If the student requested a career change, is the curriculum genuinely designed for the new career rather than the old one?
- Did I retain only existing material that is useful and relevant?
- Are essential skills or prerequisites missing?
- Are the tasks specific, practical, and verifiable?
- Is the learning sequence sensible?
- Does each project depend on previously taught skills?
- Does the final output follow the required JSON structure and contain no extra commentary?

Correct any weaknesses before producing the final JSON.

========================
OUTPUT REQUIREMENTS
========================

Return ONLY valid JSON, without Markdown fences or commentary.

Use this exact structure:

{{
  "title": "Roadmap title",
  "target_role": "The student's intended target role",
  "milestones": [
    {{
      "title": "Specific milestone title",
      "description": "The capability the learner should gain",
      "topics_to_learn": [
        "Specific concept or topic",
        "Another specific concept"
      ],
      "tasks": [
        "A specific learning task with practice and a completion result."
      ],
      "project": "A practical project for this milestone, or null",
      "completion_criteria": [
        "An observable result that demonstrates the learner has achieved the milestone"
      ],
      "prerequisites": [
        "A previous milestone or prerequisite skill, or an empty list if none"
      ]
    }}
  ]
}}

Every milestone must include all seven fields.
`topics_to_learn` and `completion_criteria` must contain at least
one specific, meaningful item each.
Every task must be a non-empty, actionable string.
`project` may be null, and `prerequisites` may be empty when appropriate.

Return the complete revised roadmap, not a description of changes.
Do not include milestone status or progress-status fields.
"""

    response = llm.invoke(prompt)

    try:
        raw_output = response.content.strip()
        raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
        raw_output = re.sub(r"\s*```$", "", raw_output)

        result = json.loads(raw_output)
        milestones = [
            RoadmapMilestone.model_validate(item).model_dump()
            for item in result["milestones"]
        ]

        return {
            "title": result["title"],
            "target_role": result.get("target_role"),
            "milestones": milestones,
        }

    except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as exc:
        print("REVISION PARSE/VALIDATION ERROR:", repr(exc))
        raise ValueError("Roadmap model returned an invalid revised roadmap format") from exc