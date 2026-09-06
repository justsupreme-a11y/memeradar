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
--
-- [2026-09 정상화] 기존 방식(조회수 ÷ 경과시간)은 소스별로 스케일이 완전히
-- 달라 "진짜 핫한지"를 비교할 수 없었음:
--   - view_count/like_count/comment_count가 없는 소스(kym, 고구마팜, 패션매거진,
--     Giphy)는 velocity_score가 항상 0으로 고정 → HOT 정렬·확산속도 배지에서
--     원천적으로 배제
--   - YouTube 크롤러가 자체적으로 계산하는 hype_score(로그 스케일 + 신선도
--     가중치, 조회수 절대값 쏠림을 완화하도록 설계됨)는 extra 필드에만 저장되고
--     정작 velocity_score/HOT 정렬에는 반영되지 않아 연결이 끊겨 있었음
--   - 순수 조회수÷시간 방식은 스케일이 없어, 조회수 100만짜리 영상 하나가
--     경과시간만 짧으면 무조건 최상단을 차지 — 실제 확산 속도가 아니라 규모만
--     반영하는 문제
--
-- 아래는 모든 소스에 동일한 로그 스케일 공식을 적용해 스케일을 통일한 버전.
-- view_count/like_count/comment_count가 전혀 없는 소스는 정직하게 0점 처리됨
-- (가짜로 "핫하다"고 표시하지 않음).
create or replace function update_velocity()
returns trigger as $$
declare
  hours_since numeric;
begin
  -- 신선도 보정 — 게시 직후 분모가 0에 가까워지며 점수가 무한대로 튀는 것 방지
  hours_since := greatest(extract(epoch from (now() - new.collected_at)) / 3600, 1.0);

  new.velocity_score = (
      (log(greatest(new.view_count, 1))       * 0.55) +
      (log(greatest(new.like_count + 1, 1))    * 0.20) +
      (log(greatest(new.comment_count + 1, 1)) * 0.25)
    ) / sqrt(hours_since);

  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_velocity
before insert or update on memes
for each row execute function update_velocity();
