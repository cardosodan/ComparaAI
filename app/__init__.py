"""App factory do ComparaAI — cria e configura a instância do Flask.

Padrão de fábrica (`create_app`) em vez de uma instância global de módulo:
permite criar múltiplas instâncias configuradas de forma diferente (ex.
uma pra testes com banco em memória), sem precisar de nenhum import
condicional espalhado pelo resto do código.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from config import Config

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # garante que os modelos são conhecidos por db.create_all()/migrations, mesmo sem uso direto aqui

    from app.routes.main import main_bp
    from app.routes.product import product_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(product_bp)

    @app.context_processor
    def injetar_globais_do_layout():
        """Dados usados pelo navbar/footer em TODA página (components/navbar.html,
        components/footer.html) — centralizado aqui pra não repetir a mesma
        query em cada rota que renderiza um template."""
        from datetime import datetime

        from app.models import Category

        categorias = Category.query.order_by(Category.active.desc(), Category.name).all()
        return {"categorias_nav": categorias, "ano_atual": datetime.utcnow().year}

    return app
