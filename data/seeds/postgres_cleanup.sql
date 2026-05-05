-- Cleanup script for Postgres: remove all seedable data and reset IDs
-- Safe for partial persisted data: leaves tables empty and identity counters reset.
-- Run BEFORE loading postgres_seed.sql

DO $$
BEGIN
	IF to_regclass('public.restaurants') IS NOT NULL
		 OR to_regclass('public.menus') IS NOT NULL
		 OR to_regclass('public.reservations') IS NOT NULL
		 OR to_regclass('public.orders') IS NOT NULL
		 OR to_regclass('public.users') IS NOT NULL THEN

		EXECUTE 'TRUNCATE TABLE
			orders,
			reservations,
			menus,
			restaurants,
			users
		RESTART IDENTITY CASCADE';
	ELSE
		RAISE NOTICE 'No seed tables found yet. Skipping truncate.';
	END IF;
END $$;

-- Verify cleanup
DO $$
DECLARE
	v_count BIGINT;
BEGIN
	RAISE NOTICE 'Cleanup complete. Current row counts:';

	IF to_regclass('public.orders') IS NOT NULL THEN
		EXECUTE 'SELECT COUNT(*) FROM orders' INTO v_count;
		RAISE NOTICE 'orders: %', v_count;
	ELSE
		RAISE NOTICE 'orders: table not found';
	END IF;

	IF to_regclass('public.reservations') IS NOT NULL THEN
		EXECUTE 'SELECT COUNT(*) FROM reservations' INTO v_count;
		RAISE NOTICE 'reservations: %', v_count;
	ELSE
		RAISE NOTICE 'reservations: table not found';
	END IF;

	IF to_regclass('public.menus') IS NOT NULL THEN
		EXECUTE 'SELECT COUNT(*) FROM menus' INTO v_count;
		RAISE NOTICE 'menus: %', v_count;
	ELSE
		RAISE NOTICE 'menus: table not found';
	END IF;

	IF to_regclass('public.restaurants') IS NOT NULL THEN
		EXECUTE 'SELECT COUNT(*) FROM restaurants' INTO v_count;
		RAISE NOTICE 'restaurants: %', v_count;
	ELSE
		RAISE NOTICE 'restaurants: table not found';
	END IF;

	IF to_regclass('public.users') IS NOT NULL THEN
		EXECUTE 'SELECT COUNT(*) FROM users' INTO v_count;
		RAISE NOTICE 'users: %', v_count;
	ELSE
		RAISE NOTICE 'users: table not found';
	END IF;
END $$;
