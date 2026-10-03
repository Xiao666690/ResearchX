
from fastapi import APIRouter, Depends, HTTPException
from core.backend.router.req_res_schema import TranslateRequest
from core.backend.services.translate import Translator
from core.backend.utils.utils import get_current_user

router = APIRouter()


@router.post("/translate")
def translate(translatetext: TranslateRequest, user=Depends(get_current_user)):
    if len(translatetext.text) > 12000:
        raise HTTPException(status_code=413, detail="单次翻译请少于 12000 个字符")
    try:
        result = Translator().translate(translatetext.text)
    except (ImportError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status_code": 200, "msg": "translated offline", "data": {"text": result}}
