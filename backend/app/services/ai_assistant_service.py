"""
AI Assistant — natural language query interface.

Uses Groq (OpenAI-compatible tool-calling API) instead of the Anthropic
API — switched after the Anthropic account used for testing hit a
billing/credit gate. Groq's free tier is sufficient for this assessment's
usage volume. The tool-execution logic (_execute_tool and everything it
calls) is unchanged from the original Anthropic-based version — only the
outer request/response harness differs, since Groq's tool-calling format
follows OpenAI's schema (tools use "type": "function" wrappers, tool
results are separate "tool" role messages keyed by tool_call_id) rather
than Anthropic's content-block format.

Design: read-only by construction. Every tool this assistant can call is a
lookup/aggregate method on an existing repository — none of them mutate
data. "Where is Rahul sitting?" is answerable; "move Rahul to Floor 2" is
not, even though seat-transfer exists elsewhere in the API. An NL-driven
mutation surface is a much larger safety/validation problem (ambiguous
name resolution, no confirmation step, no undo) than this assessment
calls for.
"""
import json

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.seat_repository import SeatRepository

# Groq's tool schema follows OpenAI's function-calling format: each tool is
# wrapped in {"type": "function", "function": {...}}, unlike Anthropic's
# flatter {"name": ..., "input_schema": ...} shape used in the original version.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_employee_seat",
            "description": "Find where a specific employee is currently sitting (seat number). Use for 'Where is X sitting?'",
            "parameters": {
                "type": "object",
                "properties": {"employee_name": {"type": "string", "description": "Full or partial name of the employee"}},
                "required": ["employee_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_zone_neighbors",
            "description": "Find who sits near/beside a specific employee (same zone). Use for 'Who sits beside/near X?'",
            "parameters": {
                "type": "object",
                "properties": {"employee_name": {"type": "string"}},
                "required": ["employee_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_vacant_seats_on_floor",
            "description": "Count vacant/empty seats on a specific floor number. Use for 'How many empty seats on Floor X?'",
            "parameters": {
                "type": "object",
                "properties": {"floor_number": {"type": "integer"}},
                "required": ["floor_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_employees_for_client",
            "description": "List employees currently working on projects for a specific client. Use for 'List employees working for Client X'",
            "parameters": {
                "type": "object",
                "properties": {"client_name": {"type": "string"}},
                "required": ["client_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_employees",
            "description": "General fallback search by name, employee code, or email when no more specific tool fits.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]

# Groq's currently-recommended tool-use model. Groq's available model list
# changes over time (models get deprecated/replaced) — if this specific
# model name ever 404s, check https://console.groq.com/docs/models for
# the current tool-use-capable model and swap it in here.
MODEL_NAME = "llama-3.3-70b-versatile"


class AIAssistantService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.employees = EmployeeRepository(db)
        self.seats = SeatRepository(db)
        self.projects = ProjectRepository(db)
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    async def _execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "find_employee_seat":
            rows, _ = await self.employees.search(query=tool_input["employee_name"], page=1, page_size=1)
            if not rows:
                return f"No employee found matching '{tool_input['employee_name']}'."
            emp = rows[0]
            allocation = await self.seats.get_active_allocation_for_employee(emp.id)
            if allocation is None:
                return f"{emp.full_name} does not currently have an assigned seat."
            seat = allocation.seat
            return f"{emp.full_name} sits at seat {seat.seat_number}."

        if name == "find_zone_neighbors":
            rows, _ = await self.employees.search(query=tool_input["employee_name"], page=1, page_size=1)
            if not rows:
                return f"No employee found matching '{tool_input['employee_name']}'."
            emp = rows[0]
            zone_name, neighbors = await self.seats.get_zone_neighbors(emp.id)
            if zone_name is None:
                return f"{emp.full_name} does not currently have an assigned seat, so no neighbors to report."
            if not neighbors:
                return f"{emp.full_name} sits in {zone_name}, with no other currently-seated colleagues nearby."
            return f"{emp.full_name} sits in {zone_name}, near: {', '.join(neighbors[:15])}."

        if name == "count_vacant_seats_on_floor":
            count = await self.seats.count_vacant_by_floor_number(tool_input["floor_number"])
            return f"There are {count} vacant seats on Floor {tool_input['floor_number']}."

        if name == "list_employees_for_client":
            names = await self.projects.employees_by_client(tool_input["client_name"])
            if not names:
                return f"No employees found currently assigned to projects for client '{tool_input['client_name']}'."
            return f"{len(names)} employees working for {tool_input['client_name']}: " + ", ".join(names[:25])

        if name == "search_employees":
            rows, total = await self.employees.search(query=tool_input["query"], page=1, page_size=10)
            if not rows:
                return f"No employees found matching '{tool_input['query']}'."
            names = [f"{e.full_name} ({e.designation})" for e in rows]
            return f"{total} matches found. Showing up to 10: " + ", ".join(names)

        return f"Unknown tool: {name}"

    async def ask(self, question: str) -> tuple[str, bool]:
        if self.client is None:
            return (
                "The AI Assistant isn't configured — set GROQ_API_KEY in the backend environment to enable natural language queries.",
                False,
            )

        system_prompt = (
            "You are the AI Assistant for an enterprise seat allocation system. "
            "Answer the user's question by calling the appropriate tool(s), then summarize "
            "the result in one or two clear, friendly sentences. If the question doesn't map "
            "to any available tool or capability (e.g. it asks to change/allocate something, "
            "which this assistant cannot do), say so plainly and suggest what it CAN help with "
            "instead of guessing."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        response = await self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            max_tokens=1024,
        )
        choice = response.choices[0]

        if choice.finish_reason != "tool_calls" or not choice.message.tool_calls:
            text = choice.message.content or "I couldn't determine how to answer that."
            return text, False

        # Groq/OpenAI-style: append the assistant's tool-call message, then
        # one "tool" role message per call (keyed by tool_call_id), unlike
        # Anthropic's single "user" message wrapping multiple tool_results.
        messages.append(choice.message)
        for tool_call in choice.message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result_text = await self._execute_tool(tool_call.function.name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_text,
                }
            )

        final = await self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            max_tokens=1024,
        )
        text = final.choices[0].message.content or "I found some data but couldn't summarize it clearly."
        return text, True