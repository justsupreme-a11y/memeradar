-- 밈레이더 — velocity_score 정상화 마이그레이션 (2026-09)
-- Supabase SQL Editor에 붙여넣고 실행 (1회성)
--
-- 배경: 기존 update_velocity() 트리거는 "조회수 ÷ 경과시간"만 사용해
--   1) view_count/like_count/comment_count를 아예 수집하지 않는 소스
--      (kym, 고구마팜, 패션매거진, Giphy)는 velocity_score가 항상 0으로 고정되어
--      HOT 정렬·확산속도 배지에서 원천적으로 배제됨
--   2) YouTube 크롤러가 자체 계산하는 hype_score(로그 스케일 + 신선도 보정,
--      조회수 절대값 쏠림 완화용으로 설계됨)는 extra 필드에만 저장되고
--      실제 velocity_score에는 전혀 반영되지 않음
--   3) 조회수÷시간 방식 자체가 스케일이 없어 조회수 규모가 큰 콘텐츠가
--      "확산 속도"와 무관하게 항상 상위를 차지
--
-- 아래는 모든 소스에 동일한 로그 스케일 공식(조회수 55% + 좋아요 20% + 댓글 25%,
-- 신선도로 나눔)을 적용해 스케일을 통일. 지표가 전혀 없는 소스는 정직하게 0점
-- 처리됨 (가짜로 "핫하다"고 표시하지 않음).

create or replace function update_velocity()
returns trigger as $$
declare
  hours_since numeric;
begin
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

-- 기존에 쌓인 행들은 트리거가 다시 실행돼야 새 공식으로 재계산됨 —
-- 전체 행에 대해 트리거를 강제로 재실행 (내용은 그대로, updated_at만 갱신)
update memes set updated_at = updated_at;
