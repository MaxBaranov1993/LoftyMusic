"""Seed the database with test data."""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lofty.config import settings
from lofty.models.base import Base
from lofty.models.job import GenerationJob, JobStatus
from lofty.models.user import User


async def seed():
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Create test user
        user = User(
            clerk_id="user_dev_seed_001",
            email="dev@lofty.local",
            display_name="Dev User",
        )
        session.add(user)
        await session.flush()

        # Create sample jobs
        prompts = [
            "upbeat electronic dance music with synth leads",
            "calm acoustic guitar with gentle rain sounds",
            "epic orchestral cinematic trailer music",
        ]

        for prompt in prompts:
            job = GenerationJob(
                user_id=user.id,
                status=JobStatus.PENDING,
                prompt=prompt,
                duration_seconds=10.0,
                model_name="musicgen-small",
                generation_params={"temperature": 1.0, "top_k": 250, "guidance_scale": 3.0},
            )
            session.add(job)

        await session.commit()
        print(f"Seeded user: {user.clerk_id} ({user.id})")
        print(f"Seeded {len(prompts)} sample jobs")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
