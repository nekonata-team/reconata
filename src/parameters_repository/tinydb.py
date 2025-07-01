from pathlib import Path

from tinydb import Query, TinyDB

from .parameters_repository import Parameters, ParametersRepository


class TinyDBParametersRepository(ParametersRepository):
    """TinyDBをバックエンドとして使用するパラメータリポジトリ。"""

    def __init__(self, db_path: Path = Path("./data/db.json")):
        # 親ディレクトリがなければ作成
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = TinyDB(db_path, indent=4, ensure_ascii=False)

    def get_parameters(self, guild_id: int) -> Parameters:
        """ギルドIDでパラメータを検索し、なければデフォルト値で返す。"""
        Record = Query()
        result = self.db.get(Record.guild_id == guild_id)

        if result:
            # Pydanticモデルに変換
            return Parameters(**result["parameters"])

        return Parameters()

    def set_parameters(self, guild_id: int, parameters: Parameters) -> None:
        """パラメータを設定（存在すれば更新、なければ挿入）。"""
        Record = Query()
        data_to_store = {"guild_id": guild_id, "parameters": parameters.model_dump()}
        self.db.upsert(data_to_store, Record.guild_id == guild_id)

    def reset_parameters(self, guild_id: int) -> None:
        """ギルドIDに紐づくパラメータを削除する。"""
        Record = Query()
        self.db.remove(Record.guild_id == guild_id)
