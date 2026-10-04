import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
conn = sqlite3.connect("characters.db")
conn.row_factory = sqlite3.Row
conn.execute("""
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    hp INTEGER NOT NULL
)
""")

class CharacterCreate(BaseModel):
    name: str
    hp: int

class CharacterPatch(BaseModel):
    name: str | None = None
    hp: int | None = None

class CharacterResponse(BaseModel):
    id: int
    name: str
    hp: int


def get_character_or_404(target_id: int):
    cursor = conn.execute("""
    SELECT id, name, hp
    FROM characters
    WHERE id = ?
    """,
    (target_id,))

    data = cursor.fetchone()

    if data is None:
        raise HTTPException(
            status_code=404,
            detail="캐릭터를 찾을 수 없습니다."
        )

    return data


@app.post("/characters", response_model=CharacterResponse)
def post_char(character: CharacterCreate):
    cursor = conn.execute(
        """
        INSERT INTO characters (name, hp)
        VALUES (?, ?)
        """,
        (character.name, character.hp)
    )

    conn.commit()

    char_dict = character.model_dump()
    char_dict["id"] = cursor.lastrowid

    return char_dict


@app.get("/characters/{target_id}", response_model=CharacterResponse)
def get_char(target_id: int):
    data = get_character_or_404(target_id)
    return dict(data)


@app.get("/characters", response_model=list[CharacterResponse])
def get_all_char():
    cursor = conn.execute("""
    SELECT id, name, hp
    FROM characters
    """)

    data = cursor.fetchall()

    return [dict(row) for row in data]


@app.delete("/characters/{target_id}", response_model=CharacterResponse)
def del_char(target_id: int):
    data = get_character_or_404(target_id)

    conn.execute("""
    DELETE FROM characters
    WHERE id = ?
    """,
    (target_id,))

    conn.commit()

    return dict(data)


@app.put("/characters/{target_id}", response_model=CharacterResponse)
def put_char(target_id: int, character: CharacterCreate):
    get_character_or_404(target_id)

    conn.execute("""
    UPDATE characters
    SET name = ?, hp = ?
    WHERE id = ?
    """,
    (character.name, character.hp, target_id))

    conn.commit()

    char_dict = character.model_dump()
    char_dict["id"] = target_id

    return char_dict


@app.patch("/characters/{target_id}", response_model=CharacterResponse)
def patch_char(target_id: int, character: CharacterPatch):
    data = get_character_or_404(target_id)

    updates = character.model_dump(exclude_unset=True)

    if not updates:
        return dict(data)

    for updated in updates.values():
        if updated is None:
            raise HTTPException(
                status_code=400,
                detail="null 요청은 허용되지 않습니다."
            )
    
    set_clauses = []
    params = []

    for key, value in updates.items():
        set_clauses.append(f"{key} = ?")
        params.append(value)

    params.append(target_id)

    set_query = ", ".join(set_clauses)

    conn.execute(f"""
    UPDATE characters
    SET {set_query}
    WHERE id = ?
    """,
    params)

    conn.commit()

    result = dict(data)
    result.update(updates)

    return result