"""One-time script to create the users/auth tables and seed the admin account."""
import os
import sys
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import get_db_connection
from auth import hash_password


def run():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Run migration
        with open(os.path.join(os.path.dirname(__file__), 'migrations', 'create_users_table.sql'), 'r', encoding='utf-8') as f:
            cursor.execute(f.read())

        # Seed default role page access
        pages = ['index', 'gpu', 'cpu', 'computers', 'laptops', 'lenses', 'project_board', 'models', 'profile']
        default_access = {
            'user': ['index', 'gpu', 'cpu', 'laptops'],
            'power_user': ['index', 'gpu', 'cpu', 'computers', 'laptops', 'lenses', 'models', 'profile'],
            'mod': ['index', 'gpu', 'cpu', 'computers', 'laptops', 'lenses', 'project_board', 'models', 'profile'],
            'admin': ['index', 'gpu', 'cpu', 'computers', 'laptops', 'lenses', 'project_board', 'models', 'admin', 'profile', 'stats']
        }
        for role, allowed in default_access.items():
            cursor.execute(
                """
                INSERT INTO role_page_access (role, allowed_pages, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (role)
                DO UPDATE SET allowed_pages = EXCLUDED.allowed_pages, updated_at = NOW()
                """,
                (role, allowed)
            )

        # Seed admin account with password 'dators'
        cursor.execute(
            """
            INSERT INTO users (username, email, role, password_hash, subscription_status, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, true, NOW(), NOW())
            ON CONFLICT (username)
            DO UPDATE SET password_hash = EXCLUDED.password_hash,
                          role = EXCLUDED.role,
                          is_active = true,
                          updated_at = NOW()
            """,
            ('admin', 'admin@ss-crawler.local', 'admin', hash_password('dators'), 'active')
        )

        # Seed subscription plans
        plans = [
            ('Free', 'free', None, 'monthly', 'user', ['gpu', 'cpu', 'laptops']),
            ('Basic', 'basic', 5.00, 'monthly', 'user', ['index', 'gpu', 'cpu', 'laptops']),
            ('Pro', 'pro', 10.00, 'monthly', 'power_user', ['index', 'gpu', 'cpu', 'computers', 'laptops', 'lenses', 'models', 'profile']),
            ('Enterprise', 'enterprise', 25.00, 'monthly', 'mod', ['index', 'gpu', 'cpu', 'computers', 'laptops', 'lenses', 'project_board', 'models', 'profile'])
        ]
        for name, slug, price, interval, role, features in plans:
            cursor.execute(
                """
                INSERT INTO subscription_plans (name, slug, price_eur, billing_interval, role_grant, features, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, true)
                ON CONFLICT (slug)
                DO UPDATE SET price_eur = EXCLUDED.price_eur,
                              role_grant = EXCLUDED.role_grant,
                              features = EXCLUDED.features,
                              is_active = true
                """,
                (name, slug, price, interval, role, features)
            )

        conn.commit()
        print("Auth tables and admin account created/updated.")
        print("Login: admin / dators")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    run()
