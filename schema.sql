-- Supabase SQL Editor에 붙여넣고 실행하세요

create table if not exists memes (
  id              bigserial primary key,
  title           text        not null,
  url             text        not null,
  source          text        not null,  -- dcinside | fmkorea | youtube
  platform        text        not null,  -- domestic | global
  image_url       text        default '',
  view_count      integer     default 0,
  like_count      integer     default 0,
  comment_count   integer     default 0,
  content_hash    text        unique not null,  -- 중복 방지
  flow_type       text,  -- inflow | independent | export (분류 레이어가 채움)
  lifecycle_stage text,  -- seed | spread | peak | fade
  extra           jsonb       default '{}',
  collected_at    timestamptz default now()
);

-- 자주 쓰는 쿼리 최적화 인덱스
create index if not exists idx_memes_source        on memes(source);
create index if not exists idx_memes_platform      on memes(platform);
create index if not exists idx_memes_flow_type     on memes(flow_type);
create index if not exists idx_memes_collected_at  on memes(collected_at desc);
create index if not exists idx_memes_view_count    on memes(view_count desc);
