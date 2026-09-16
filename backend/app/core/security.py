"""Bölüm 20: Güvenlik Altyapısı — JWT kimlik doğrulama, RBAC yetkilendirme."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.orm import Kullanici

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/giris")


def sifre_dogrula(duz_sifre: str, hash_sifre: str) -> bool:
    return pwd_context.verify(duz_sifre, hash_sifre)


def sifre_hashle(sifre: str) -> str:
    return pwd_context.hash(sifre)


def token_olustur(data: dict, sure: timedelta | None = None) -> str:
    payload = data.copy()
    son_tarih = datetime.utcnow() + (sure or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"exp": son_tarih})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def gecerli_kullanici_al(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> Kullanici:
    yetkisiz_hata = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulanamadı",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise yetkisiz_hata
    except JWTError:
        raise yetkisiz_hata

    kullanici = db.query(Kullanici).filter(Kullanici.email == email).first()
    if kullanici is None:
        raise yetkisiz_hata
    return kullanici


def rol_gerekli(*izinli_roller: str):
    """RBAC: belirli endpoint'lere sadece belirli rollerin erişimine izin verir.
    Kullanım: @router.delete(...); dependencies=[Depends(rol_gerekli("admin"))]
    """
    def kontrol(kullanici: Kullanici = Depends(gecerli_kullanici_al)) -> Kullanici:
        if kullanici.rol not in izinli_roller:
            raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
        return kullanici
    return kontrol
