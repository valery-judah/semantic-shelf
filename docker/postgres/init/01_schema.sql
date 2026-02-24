CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR NOT NULL,
    external_idp_id VARCHAR NOT NULL,
    domain_preferences JSON NOT NULL,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_external_idp_id ON users (external_idp_id);

CREATE TABLE IF NOT EXISTS books (
    id VARCHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    authors JSON NOT NULL,
    genres JSON NOT NULL,
    publication_year INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source TEXT NOT NULL DEFAULT 'goodbooks',
    goodreads_book_id BIGINT,
    best_book_id BIGINT,
    work_id BIGINT,
    books_count INTEGER,
    isbn TEXT,
    isbn13 TEXT,
    language_code TEXT,
    average_rating NUMERIC(3, 2),
    ratings_count INTEGER,
    work_ratings_count INTEGER,
    work_text_reviews_count INTEGER,
    ratings_1 INTEGER,
    ratings_2 INTEGER,
    ratings_3 INTEGER,
    ratings_4 INTEGER,
    ratings_5 INTEGER,
    original_title TEXT,
    description TEXT,
    pages INTEGER,
    publish_date_raw TEXT,
    image_url TEXT,
    small_image_url TEXT,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_books_goodreads_book_id ON books (goodreads_book_id);

CREATE TABLE IF NOT EXISTS dataset_users (
    user_id BIGINT NOT NULL,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id INTEGER NOT NULL,
    tag_name TEXT NOT NULL,
    PRIMARY KEY (tag_id)
);

CREATE TABLE IF NOT EXISTS ratings (
    user_id BIGINT NOT NULL,
    book_id VARCHAR(36) NOT NULL,
    rating INTEGER NOT NULL,
    CONSTRAINT ck_ratings_rating_1_5 CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT fk_ratings_user_id_dataset_users FOREIGN KEY (user_id)
        REFERENCES dataset_users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_ratings_book_id_books FOREIGN KEY (book_id)
        REFERENCES books(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, book_id)
);
CREATE INDEX IF NOT EXISTS ix_ratings_book_id ON ratings (book_id);

CREATE TABLE IF NOT EXISTS to_read (
    user_id BIGINT NOT NULL,
    book_id VARCHAR(36) NOT NULL,
    CONSTRAINT fk_to_read_user_id_dataset_users FOREIGN KEY (user_id)
        REFERENCES dataset_users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_to_read_book_id_books FOREIGN KEY (book_id)
        REFERENCES books(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, book_id)
);
CREATE INDEX IF NOT EXISTS ix_to_read_book_id ON to_read (book_id);

CREATE TABLE IF NOT EXISTS book_tags (
    goodreads_book_id BIGINT NOT NULL,
    tag_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    CONSTRAINT fk_book_tags_goodreads_book_id_books FOREIGN KEY (goodreads_book_id)
        REFERENCES books(goodreads_book_id) ON DELETE CASCADE,
    CONSTRAINT fk_book_tags_tag_id_tags FOREIGN KEY (tag_id)
        REFERENCES tags(tag_id) ON DELETE CASCADE,
    PRIMARY KEY (goodreads_book_id, tag_id)
);
CREATE INDEX IF NOT EXISTS ix_book_tags_tag_id ON book_tags (tag_id);

DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('a5f7f7c1f231');
