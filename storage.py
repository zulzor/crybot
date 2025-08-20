"""
Слой хранилища: SQLite / JSON / Hybrid

Назначение:
- Единый KV-интерфейс по пространствам имён (wallets, inventories, profiles, clans, marriages, meta)
- Поддержка .env переключателя STORAGE_BACKEND=sqlite|json|hybrid
- HYBRID_EXPORT_JSON=true|false — экспорт снапшотов JSON при изменениях
- IMPORT_JSON_ON_FIRST_RUN=true|false — разовый импорт из JSON при пустой БД
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


class BaseKVStorage:
    def get(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def set(self, namespace: str, key: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def get_all(self, namespace: str) -> Dict[str, Dict[str, Any]]:
        raise NotImplementedError

    def is_empty(self, namespace: str) -> bool:
        return len(self.get_all(namespace)) == 0


class SQLiteKVStorage(BaseKVStorage):
    def __init__(self, db_path: str):
        self.db_path = db_path
        _ensure_dir(Path(db_path).parent if Path(db_path).parent.as_posix() != '' else Path('.'))
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS kv (namespace TEXT, id TEXT, data TEXT, PRIMARY KEY(namespace, id))"
        )
        self.conn.commit()

    def get(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT data FROM kv WHERE namespace=? AND id=?",
            (namespace, key),
        )
        row = cur.fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except Exception:
            return None

    def set(self, namespace: str, key: str, data: Dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False)
        self.conn.execute(
            "INSERT OR REPLACE INTO kv(namespace,id,data) VALUES(?,?,?)",
            (namespace, key, payload),
        )
        self.conn.commit()

    def get_all(self, namespace: str) -> Dict[str, Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT id, data FROM kv WHERE namespace=?",
            (namespace,),
        )
        out: Dict[str, Dict[str, Any]] = {}
        for key, data_str in cur.fetchall():
            try:
                out[str(key)] = json.loads(data_str)
            except Exception:
                continue
        return out


class JSONKVStorage(BaseKVStorage):
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        _ensure_dir(self.data_dir)

    def _file(self, namespace: str) -> Path:
        return self.data_dir / f"{namespace}.json"

    def _load_file(self, namespace: str) -> Dict[str, Dict[str, Any]]:
        fp = self._file(namespace)
        if not fp.exists():
            return {}
        try:
            with fp.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_file(self, namespace: str, mapping: Dict[str, Dict[str, Any]]) -> None:
        fp = self._file(namespace)
        with fp.open("w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

    def get(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        return self._load_file(namespace).get(str(key))

    def set(self, namespace: str, key: str, data: Dict[str, Any]) -> None:
        mapping = self._load_file(namespace)
        mapping[str(key)] = data
        self._save_file(namespace, mapping)

    def get_all(self, namespace: str) -> Dict[str, Dict[str, Any]]:
        return self._load_file(namespace)


class HybridStorage(BaseKVStorage):
    def __init__(self, primary: BaseKVStorage, shadow_json: JSONKVStorage, hybrid_export: bool, import_on_first_run: bool):
        self.primary = primary
        self.shadow = shadow_json
        self.hybrid_export = hybrid_export
        self.import_on_first_run = import_on_first_run
        if self.import_on_first_run:
            self._import_if_needed()

    def _import_if_needed(self) -> None:
        # Импортируем известные пространства, если они пустые в primary
        namespaces = [
            "wallets",
            "inventories",
            "profiles",
            "clans",
            "marriages",
            "meta",
        ]
        for ns in namespaces:
            if self.primary.is_empty(ns):
                all_json = self.shadow.get_all(ns)
                if all_json:
                    for key, data in all_json.items():
                        self.primary.set(ns, key, data)

    def get(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        return self.primary.get(namespace, key)

    def set(self, namespace: str, key: str, data: Dict[str, Any]) -> None:
        self.primary.set(namespace, key, data)
        if self.hybrid_export:
            # Обновляем JSON снапшот целиком (простая реализация)
            snapshot = self.primary.get_all(namespace)
            # cast keys to str
            snapshot = {str(k): v for k, v in snapshot.items()}
            self.shadow._save_file(namespace, snapshot)

    def get_all(self, namespace: str) -> Dict[str, Dict[str, Any]]:
        return self.primary.get_all(namespace)


def get_storage_from_env() -> BaseKVStorage:
    backend = (os.getenv("STORAGE_BACKEND", "sqlite").strip().lower() or "sqlite")
    db_path = os.getenv("DB_PATH", "./crycat.db").strip()
    hybrid_export = _env_bool("HYBRID_EXPORT_JSON", False)
    import_on_first_run = _env_bool("IMPORT_JSON_ON_FIRST_RUN", True)

    if backend == "json":
        return JSONKVStorage("data")
    if backend == "hybrid":
        primary = SQLiteKVStorage(db_path)
        shadow = JSONKVStorage("data")
        return HybridStorage(primary, shadow, hybrid_export, import_on_first_run)
    # default sqlite
    return SQLiteKVStorage(db_path)

