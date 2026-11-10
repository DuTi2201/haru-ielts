-- Database half of the acceptance audit (the seed half is scripts/content_audit.py).
-- psql "$DATABASE_URL" -f scripts/audit_db.sql      every row: check | value | expected
\pset footer off
SELECT 'DB-01 article cards no article lists' AS check,
       (SELECT count(*) FROM content.vocab_item v WHERE v.lesson_id IS NULL
          AND NOT EXISTS (SELECT 1 FROM editorial.editorial_article e WHERE v.id = ANY(e.vocab_ids)))
     + (SELECT count(*) FROM content.grammar_point g WHERE g.lesson_id IS NULL
          AND NOT EXISTS (SELECT 1 FROM editorial.editorial_article e WHERE g.id = ANY(e.grammar_ids))) AS value, '0' AS expected
UNION ALL SELECT 'DB-01 article words that copy a course card',
       (SELECT count(*) FROM content.vocab_item o WHERE o.lesson_id IS NULL
          AND EXISTS (SELECT 1 FROM content.vocab_item c WHERE c.lesson_id IS NOT NULL AND c.hangul = o.hangul)), '0'
UNION ALL SELECT 'DB-02 same word twice in one lesson',
       (SELECT count(*) FROM (SELECT lesson_id, hangul FROM content.vocab_item WHERE lesson_id IS NOT NULL
          GROUP BY 1, 2 HAVING count(*) > 1) d), '0'
UNION ALL SELECT 'DB-02 review rows pointing at no card',
       (SELECT count(*) FROM public.item_state s WHERE NOT EXISTS (
          SELECT 1 FROM content.vocab_item v WHERE s.item_type = 'vocab_item' AND v.id = s.item_id UNION ALL
          SELECT 1 FROM content.grammar_point g WHERE s.item_type = 'grammar_point' AND g.id = s.item_id)), '0'
UNION ALL SELECT 'DB-03 lesson levels present',
       (SELECT count(DISTINCT level) FROM content.lesson), '6'
UNION ALL SELECT 'DB-04 editorial ids pointing at no card',
       (SELECT count(*) FROM editorial.editorial_article e, unnest(e.vocab_ids) x
          WHERE NOT EXISTS (SELECT 1 FROM content.vocab_item v WHERE v.id = x))
     + (SELECT count(*) FROM editorial.editorial_article e, unnest(e.grammar_ids) x
          WHERE NOT EXISTS (SELECT 1 FROM content.grammar_point g WHERE g.id = x)), '0'
UNION ALL SELECT 'EDT-01 shown editorials with no text',
       (SELECT count(*) FROM editorial.editorial_article WHERE body_ko IS NOT NULL AND btrim(body_ko) = ''), '0 (hidden anyway)'
UNION ALL SELECT 'EDT-01 editorials over 4,000 characters',
       (SELECT count(*) FROM editorial.editorial_article WHERE length(body_ko) > 4000), 'info'
UNION ALL SELECT 'EDT-02 editorials with text but no study pack',
       (SELECT count(*) FROM editorial.editorial_article WHERE length(btrim(coalesce(body_ko, ''))) > 0 AND study_status <> 'ready'), '0'
UNION ALL SELECT 'EDT-02 editorials with text but no model outline',
       (SELECT count(*) FROM editorial.editorial_article WHERE length(btrim(coalesce(body_ko, ''))) > 0 AND model_outline IS NULL), '0'
UNION ALL SELECT 'LOOP-01 saved words not linked to a card',
       (SELECT count(*) FROM public.talk_note WHERE kind = 'word' AND vocab_item_id IS NULL), 'info (run the backfill)'
UNION ALL SELECT 'CORPUS lines shown that were judged awkward/unnatural',
       (SELECT count(*) FROM corpus.corpus_item WHERE naturalness IN ('awkward', 'unnatural')), 'all hidden by the API';
