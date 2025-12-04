import asyncio
from datetime import date, timedelta, datetime, time
from sqlalchemy import select
from db.db import get_session_maker
from models.entities import Subject, Tag, SubjectTag, SleepRecord
import random

async def seed():
    session_maker = get_session_maker()
    async with session_maker() as session:
        # 20 personajes animados
        names = [
            ("Mickey Mouse", 92, "M"), ("Bugs Bunny", 80, "M"), ("Homer Simpson", 45, "M"),
            ("Marge Simpson", 42, "F"), ("Bart Simpson", 10, "M"), ("Lisa Simpson", 8, "F"),
            ("Stewie Griffin", 1, "M"), ("Peter Griffin", 43, "M"), ("Brian Griffin", 7, "M"),
            ("SpongeBob", 22, "M"), ("Patrick Star", 20, "M"), ("Scooby Doo", 7, "M"),
            ("Shaggy Rogers", 25, "M"), ("Dora", 12, "F"), ("Diego", 13, "M"),
            ("Naruto", 17, "M"), ("Sakura", 17, "F"), ("Goku", 40, "M"),
            ("Vegeta", 42, "M"), ("Pikachu", 5, "O")
        ]
        subjects = {}
        for name, age, gender in names:
            s = (await session.execute(select(Subject).where(Subject.name == name))).scalar_one_or_none()
            if not s:
                s = Subject(name=name, age=age, gender=gender)
                session.add(s)
                await session.flush()
            subjects[name] = s

        # Tags comunes
        tag_names = ["Ejercicio", "Cafe tarde", "Pantallas noche", "Rutina consistente", "Estrés alto", "Alcohol"]
        tags = {}
        for tname in tag_names:
            t = (await session.execute(select(Tag).where(Tag.name == tname))).scalar_one_or_none()
            if not t:
                t = Tag(name=tname)
                session.add(t)
                await session.flush()
            tags[tname] = t

        # Asociar aleatoriamente 0-2 tags por sujeto (evita duplicados)
        async def link(subj, t):
            exists = (await session.execute(
                select(SubjectTag).where((SubjectTag.subject_id == subj.id) & (SubjectTag.tag_id == t.id))
            )).scalar_one_or_none()
            if not exists:
                session.add(SubjectTag(subject_id=subj.id, tag_id=t.id))

        for subj in subjects.values():
            chosen = random.sample(list(tags.values()), k=random.randint(0, 2))
            for t in chosen:
                await link(subj, t)

        base = date.today()

        # Generación de patrones por sujeto (rotado para variedad)
        time_patterns = [
            (time(22, 0), time(6, 0)),
            (time(23, 0), time(7, 0)),
            (time(22, 30), time(6, 15)),
            (time(23, 30), time(6, 45)),
            (time(0, 30), time(8, 0)),
        ]

        total_inserted = 0

        async def upsert_record(subj, d, bed_t, wake_t, dur, eff, aw):
            nonlocal total_inserted
            existing = (await session.execute(
                select(SleepRecord).where((SleepRecord.subject_id == subj.id) & (SleepRecord.record_date == d))
            )).scalar_one_or_none()
            if not existing:
                session.add(SleepRecord(
                    subject_id=subj.id,
                    record_date=d,
                    bedtime=datetime.combine(d, bed_t),
                    wakeup_time=datetime.combine(d, wake_t),
                    sleep_duration=dur,
                    sleep_efficiency=eff,
                    awakenings=aw
                ))
                total_inserted += 1

        # Queremos al menos 150 registros. Usaremos 20 sujetos * 8 días = 160 registros (mínimo).
        days_per_subject = 8

        for idx, (name, _, _) in enumerate(names):
            subj = subjects[name]
            pattern = time_patterns[idx % len(time_patterns)]
            avg_duration = round(random.uniform(5.8, 7.5), 1)
            avg_eff = random.randint(75, 92)

            for offset in range(days_per_subject):
                d = base - timedelta(days=offset)
                duration = max(3.0, round(avg_duration + random.uniform(-0.6, 0.6), 1))
                efficiency = max(50, min(100, avg_eff + random.randint(-6, 6)))
                awakenings = random.randint(0, 4)

                await upsert_record(
                    subj, d,
                    pattern[0],
                    pattern[1],
                    duration,
                    int(efficiency),
                    awakenings
                )

        # Si por alguna razón no alcanzamos 150 (por registros existentes), agregamos días extra a sujetos aleatorios.
        extra_offset = days_per_subject
        while total_inserted < 150:
            subj = random.choice(list(subjects.values()))
            d = base - timedelta(days=extra_offset)
            pattern = random.choice(time_patterns)
            duration = round(random.uniform(5.0, 8.0), 1)
            efficiency = random.randint(65, 95)
            awakenings = random.randint(0, 4)
            await upsert_record(subj, d, pattern[0], pattern[1], duration, efficiency, awakenings)
            extra_offset += 1

        await session.commit()
        print(f"✅ Seed completado: {len(subjects)} sujetos, registros insertados = {total_inserted}")

if __name__ == "__main__":
    asyncio.run(seed())
