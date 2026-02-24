CREATE SCHEMA IF NOT EXISTS import_stage;

CREATE TABLE IF NOT EXISTS import_stage.books_enriched_raw (
    row_num TEXT,
    index_num TEXT,
    authors_raw TEXT,
    average_rating_raw TEXT,
    best_book_id_raw TEXT,
    book_id_raw TEXT,
    books_count_raw TEXT,
    description_raw TEXT,
    genres_raw TEXT,
    goodreads_book_id_raw TEXT,
    image_url_raw TEXT,
    isbn_raw TEXT,
    isbn13_raw TEXT,
    language_code_raw TEXT,
    original_publication_year_raw TEXT,
    original_title_raw TEXT,
    pages_raw TEXT,
    publish_date_raw TEXT,
    ratings_1_raw TEXT,
    ratings_2_raw TEXT,
    ratings_3_raw TEXT,
    ratings_4_raw TEXT,
    ratings_5_raw TEXT,
    ratings_count_raw TEXT,
    small_image_url_raw TEXT,
    title_raw TEXT,
    work_id_raw TEXT,
    work_ratings_count_raw TEXT,
    work_text_reviews_count_raw TEXT,
    authors_2_raw TEXT
);

TRUNCATE TABLE import_stage.books_enriched_raw;

COPY import_stage.books_enriched_raw
FROM '/docker-entrypoint-seed/books_enriched.csv'
WITH (FORMAT csv, HEADER true);

INSERT INTO books (
    id,
    title,
    authors,
    genres,
    publication_year,
    created_at,
    source,
    goodreads_book_id,
    best_book_id,
    work_id,
    books_count,
    isbn,
    isbn13,
    language_code,
    average_rating,
    ratings_count,
    work_ratings_count,
    work_text_reviews_count,
    ratings_1,
    ratings_2,
    ratings_3,
    ratings_4,
    ratings_5,
    original_title,
    description,
    pages,
    publish_date_raw,
    image_url,
    small_image_url
)
SELECT
    NULLIF(TRIM(book_id_raw), '')::NUMERIC::BIGINT::TEXT AS id,
    COALESCE(NULLIF(TRIM(title_raw), ''), 'Unknown title') AS title,
    COALESCE(
        (
            SELECT to_json(ARRAY_AGG(cleaned))
            FROM (
                SELECT BTRIM(part, ' ''"') AS cleaned
                FROM UNNEST(REGEXP_SPLIT_TO_ARRAY(TRIM(BOTH '[]' FROM COALESCE(authors_raw, '')), E'\\s*,\\s*')) AS part
            ) AS normalized
            WHERE cleaned <> ''
        ),
        '[]'::JSON
    ) AS authors,
    COALESCE(
        (
            SELECT to_json(ARRAY_AGG(cleaned))
            FROM (
                SELECT BTRIM(part, ' ''"') AS cleaned
                FROM UNNEST(REGEXP_SPLIT_TO_ARRAY(TRIM(BOTH '[]' FROM COALESCE(genres_raw, '')), E'\\s*,\\s*')) AS part
            ) AS normalized
            WHERE cleaned <> ''
        ),
        '[]'::JSON
    ) AS genres,
    NULLIF(TRIM(original_publication_year_raw), '')::NUMERIC::INTEGER AS publication_year,
    NOW() AS created_at,
    'goodbooks'::TEXT AS source,
    NULLIF(TRIM(goodreads_book_id_raw), '')::NUMERIC::BIGINT AS goodreads_book_id,
    NULLIF(TRIM(best_book_id_raw), '')::NUMERIC::BIGINT AS best_book_id,
    NULLIF(TRIM(work_id_raw), '')::NUMERIC::BIGINT AS work_id,
    NULLIF(TRIM(books_count_raw), '')::NUMERIC::INTEGER AS books_count,
    NULLIF(TRIM(isbn_raw), '') AS isbn,
    NULLIF(TRIM(isbn13_raw), '') AS isbn13,
    NULLIF(TRIM(language_code_raw), '') AS language_code,
    NULLIF(TRIM(average_rating_raw), '')::NUMERIC(3, 2) AS average_rating,
    NULLIF(TRIM(ratings_count_raw), '')::NUMERIC::INTEGER AS ratings_count,
    NULLIF(TRIM(work_ratings_count_raw), '')::NUMERIC::INTEGER AS work_ratings_count,
    NULLIF(TRIM(work_text_reviews_count_raw), '')::NUMERIC::INTEGER AS work_text_reviews_count,
    NULLIF(TRIM(ratings_1_raw), '')::NUMERIC::INTEGER AS ratings_1,
    NULLIF(TRIM(ratings_2_raw), '')::NUMERIC::INTEGER AS ratings_2,
    NULLIF(TRIM(ratings_3_raw), '')::NUMERIC::INTEGER AS ratings_3,
    NULLIF(TRIM(ratings_4_raw), '')::NUMERIC::INTEGER AS ratings_4,
    NULLIF(TRIM(ratings_5_raw), '')::NUMERIC::INTEGER AS ratings_5,
    NULLIF(TRIM(original_title_raw), '') AS original_title,
    NULLIF(TRIM(description_raw), '') AS description,
    NULLIF(TRIM(pages_raw), '')::NUMERIC::INTEGER AS pages,
    NULLIF(TRIM(publish_date_raw), '') AS publish_date_raw,
    NULLIF(TRIM(image_url_raw), '') AS image_url,
    NULLIF(TRIM(small_image_url_raw), '') AS small_image_url
FROM import_stage.books_enriched_raw
WHERE NULLIF(TRIM(book_id_raw), '') IS NOT NULL
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    authors = EXCLUDED.authors,
    genres = EXCLUDED.genres,
    publication_year = EXCLUDED.publication_year,
    source = EXCLUDED.source,
    goodreads_book_id = EXCLUDED.goodreads_book_id,
    best_book_id = EXCLUDED.best_book_id,
    work_id = EXCLUDED.work_id,
    books_count = EXCLUDED.books_count,
    isbn = EXCLUDED.isbn,
    isbn13 = EXCLUDED.isbn13,
    language_code = EXCLUDED.language_code,
    average_rating = EXCLUDED.average_rating,
    ratings_count = EXCLUDED.ratings_count,
    work_ratings_count = EXCLUDED.work_ratings_count,
    work_text_reviews_count = EXCLUDED.work_text_reviews_count,
    ratings_1 = EXCLUDED.ratings_1,
    ratings_2 = EXCLUDED.ratings_2,
    ratings_3 = EXCLUDED.ratings_3,
    ratings_4 = EXCLUDED.ratings_4,
    ratings_5 = EXCLUDED.ratings_5,
    original_title = EXCLUDED.original_title,
    description = EXCLUDED.description,
    pages = EXCLUDED.pages,
    publish_date_raw = EXCLUDED.publish_date_raw,
    image_url = EXCLUDED.image_url,
    small_image_url = EXCLUDED.small_image_url;
