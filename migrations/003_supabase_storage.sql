-- Supabase only. Do not grant anon/authenticated policies for this bucket.
INSERT INTO storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
VALUES ('traffic-private','traffic-private',false,104857600,
 ARRAY['image/jpeg','image/png','video/mp4','video/webm','video/quicktime','video/x-msvideo','application/octet-stream'])
ON CONFLICT(id) DO UPDATE SET public=false,file_size_limit=104857600;
-- A restrictive policy also blocks this bucket if unrelated legacy permissive
-- policies grant broad access. Other buckets are unaffected.
DROP POLICY IF EXISTS traffic_private_deny_browser ON storage.objects;
CREATE POLICY traffic_private_deny_browser ON storage.objects AS RESTRICTIVE
FOR ALL TO anon,authenticated
USING (bucket_id <> 'traffic-private') WITH CHECK (bucket_id <> 'traffic-private');
-- The API/worker use a service-role key kept server-side. Scoped signed upload
-- and download authorizations are issued only after Flask role/ownership checks.
