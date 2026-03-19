-- 기존 테이블 초기화 후 재생성
-- Supabase SQL Editor에 붙여넣고 실행

DROP TABLE IF EXISTS memes CASCADE;

CREATE TABLE memes (
  id              bigserial primary key,

  -- 기본 정보
  title           text        not null,
  url             text        not null,
  image_url       text        default '',
  content_hash    text        unique not null,

  -- 소스 정보
  source          text        not null,  -- namuwiki | instiz | univ_tomorrow | kym | youtube_meme_ch | google_trends
  platform        text        not null,  -- domestic | global

  -- 분류
  flow_type       text,        -- inflow | independent | export
  lifecycle_stage text,        -- seed | spread | peak | fade
  category        text,        -- fb | fashion | celeb | general

  -- 지표
  view_count      integer     default 0,
  like_count      integer     default 0,
  comment_count   integer     default 0,
  velocity_score  float       default 0,  -- 확산속도 (시간당 조회수)

  -- 관련 기사/링크
  related_links   jsonb       default '[]',  -- [{title, url, source}]

  -- 메타
  extra           jsonb       default '{}',
  collected_at    timestamptz default now(),
  updated_at      timestamptz default now()
);

-- 인덱스
create index on memes(source);
create index on memes(platform);
create index on memes(flow_type);
create index on memes(lifecycle_stage);
create index on memes(category);
create index on memes(velocity_score desc);
create index on memes(collected_at desc);

-- 확산속도 자동 업데이트 함수
create or replace function update_velocity()
returns trigger as $$
begin
  new.velocity_score = case
    when extract(epoch from (now() - new.collected_at)) / 3600 < 1 then new.view_count
    else new.view_count / (extract(epoch from (now() - new.collected_at)) / 3600)
  end;
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_velocity
before insert or update on memes
for each row execute function update_velocity();
