-- RPC function to atomically increment turn count
CREATE OR REPLACE FUNCTION increment_turn(cid UUID)
RETURNS void AS $$
BEGIN
  UPDATE campaigns SET turn_count = turn_count + 1, updated_at = now() WHERE id = cid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
