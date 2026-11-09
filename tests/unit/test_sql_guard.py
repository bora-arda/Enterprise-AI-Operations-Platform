"""Unit tests for the read-only SQL guard (no database required)."""

from procurement_ai.database.sql_guard import validate_sql


class TestSqlGuard:
    def test_allows_select(self):
        assert validate_sql("SELECT 1")[0] is True

    def test_allows_cte(self):
        sql = """
            WITH totals AS (
                SELECT vendor_id, SUM(amount) AS total
                FROM invoices
                GROUP BY vendor_id
            )
            SELECT * FROM totals ORDER BY total DESC
        """
        assert validate_sql(sql)[0] is True

    def test_allows_information_schema(self):
        assert validate_sql("SELECT table_name FROM information_schema.tables")[0] is True

    def test_allows_keywords_inside_string_literals(self):
        assert validate_sql("SELECT 'drop table invoices' AS note")[0] is True

    def test_rejects_multiple_statements(self):
        valid, reason = validate_sql("SELECT 1; DROP TABLE invoices")
        assert valid is False
        assert "single" in (reason or "").lower()

    def test_rejects_dml_and_ddl(self):
        for sql in (
            "DELETE FROM invoices",
            "UPDATE invoices SET status = 'paid'",
            "INSERT INTO invoices (id) VALUES (1)",
            "DROP TABLE invoices",
            "ALTER TABLE invoices ADD COLUMN x INT",
            "TRUNCATE invoices",
        ):
            assert validate_sql(sql)[0] is False, sql

    def test_rejects_write_cte(self):
        sql = "WITH x AS (DELETE FROM invoices RETURNING *) SELECT * FROM x"
        assert validate_sql(sql)[0] is False

    def test_rejects_password_hash(self):
        valid, reason = validate_sql("SELECT password_hash FROM users")
        assert valid is False
        assert "password_hash" in (reason or "")

    def test_rejects_embedding_and_bank_details(self):
        assert validate_sql("SELECT embedding FROM documents")[0] is False
        assert validate_sql("SELECT bank_details FROM vendors")[0] is False

    def test_rejects_planner_and_checkpoint_tables(self):
        assert validate_sql("SELECT * FROM planner_decisions")[0] is False
        assert validate_sql("SELECT * FROM checkpoints")[0] is False

    def test_rejects_dangerous_functions(self):
        for sql in (
            "SELECT pg_sleep(10)",
            "SELECT pg_read_file('/etc/passwd')",
            "SELECT set_config('statement_timeout', '0', false)",
            "SELECT dblink('host=localhost', 'SELECT 1')",
        ):
            assert validate_sql(sql)[0] is False, sql

    def test_rejects_select_into(self):
        assert validate_sql("SELECT * INTO invoices_copy FROM invoices")[0] is False

    def test_rejects_row_locking(self):
        assert validate_sql("SELECT * FROM invoices FOR UPDATE")[0] is False

    def test_allows_leading_comments(self):
        sql = "-- analyst query\nSELECT COUNT(*) FROM invoices"
        assert validate_sql(sql)[0] is True

    def test_tolerates_markdown_fence(self):
        sql = "```sql\nSELECT COUNT(*) FROM invoices\n```"
        assert validate_sql(sql)[0] is True

    def test_tolerates_unmatched_trailing_quote(self):
        sql = 'SELECT COUNT(*) FROM invoices LIMIT 1"'
        assert validate_sql(sql)[0] is True
