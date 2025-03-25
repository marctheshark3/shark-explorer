from fastapi import APIRouter
from .blocks import router as blocks_router
from .transactions import router as transactions_router
from .addresses import router as addresses_router
from .info import router as info_router
from .tokens import router as tokens_router

router = APIRouter()

router.include_router(blocks_router)
router.include_router(transactions_router)
router.include_router(addresses_router)
router.include_router(info_router)
router.include_router(tokens_router) 