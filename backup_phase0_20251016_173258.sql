--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (165f042)
-- Dumped by pg_dump version 16.9

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bundle_components; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.bundle_components (
    id integer NOT NULL,
    bundle_sku_id integer NOT NULL,
    component_sku text NOT NULL,
    multiplier integer NOT NULL,
    sequence integer DEFAULT 1 NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT bundle_components_multiplier_check CHECK ((multiplier > 0))
);


ALTER TABLE public.bundle_components OWNER TO neondb_owner;

--
-- Name: bundle_components_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.bundle_components_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bundle_components_id_seq OWNER TO neondb_owner;

--
-- Name: bundle_components_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.bundle_components_id_seq OWNED BY public.bundle_components.id;


--
-- Name: bundle_skus; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.bundle_skus (
    id integer NOT NULL,
    bundle_sku text NOT NULL,
    description text NOT NULL,
    active integer DEFAULT 1 NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    updated_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT bundle_skus_active_check CHECK ((active = ANY (ARRAY[0, 1])))
);


ALTER TABLE public.bundle_skus OWNER TO neondb_owner;

--
-- Name: bundle_skus_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.bundle_skus_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bundle_skus_id_seq OWNER TO neondb_owner;

--
-- Name: bundle_skus_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.bundle_skus_id_seq OWNED BY public.bundle_skus.id;


--
-- Name: configuration_params; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.configuration_params (
    id integer NOT NULL,
    category text NOT NULL,
    parameter_name text NOT NULL,
    value text NOT NULL,
    sku text,
    notes text,
    last_updated text,
    created_at text DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.configuration_params OWNER TO neondb_owner;

--
-- Name: configuration_params_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.configuration_params_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuration_params_id_seq OWNER TO neondb_owner;

--
-- Name: configuration_params_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.configuration_params_id_seq OWNED BY public.configuration_params.id;


--
-- Name: inventory_current; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.inventory_current (
    id integer NOT NULL,
    sku text NOT NULL,
    product_name text NOT NULL,
    current_quantity integer NOT NULL,
    weekly_avg_cents integer,
    alert_level text DEFAULT 'normal'::text NOT NULL,
    reorder_point integer DEFAULT 50 NOT NULL,
    last_updated text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT inventory_current_alert_level_check CHECK ((alert_level = ANY (ARRAY['normal'::text, 'low'::text, 'critical'::text])))
);


ALTER TABLE public.inventory_current OWNER TO neondb_owner;

--
-- Name: inventory_current_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.inventory_current_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inventory_current_id_seq OWNER TO neondb_owner;

--
-- Name: inventory_current_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.inventory_current_id_seq OWNED BY public.inventory_current.id;


--
-- Name: inventory_transactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.inventory_transactions (
    id integer NOT NULL,
    date text NOT NULL,
    sku text NOT NULL,
    quantity integer NOT NULL,
    transaction_type text NOT NULL,
    notes text,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT inventory_transactions_quantity_check CHECK ((quantity <> 0)),
    CONSTRAINT inventory_transactions_transaction_type_check CHECK ((transaction_type = ANY (ARRAY['Receive'::text, 'Ship'::text, 'Adjust Up'::text, 'Adjust Down'::text, 'Repack'::text])))
);


ALTER TABLE public.inventory_transactions OWNER TO neondb_owner;

--
-- Name: inventory_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.inventory_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inventory_transactions_id_seq OWNER TO neondb_owner;

--
-- Name: inventory_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.inventory_transactions_id_seq OWNED BY public.inventory_transactions.id;


--
-- Name: lot_inventory; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.lot_inventory (
    id integer NOT NULL,
    sku text NOT NULL,
    lot text NOT NULL,
    initial_qty integer DEFAULT 0 NOT NULL,
    manual_adjustment integer DEFAULT 0 NOT NULL,
    received_date text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    notes text,
    created_at text DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at text DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.lot_inventory OWNER TO neondb_owner;

--
-- Name: lot_inventory_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.lot_inventory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lot_inventory_id_seq OWNER TO neondb_owner;

--
-- Name: lot_inventory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.lot_inventory_id_seq OWNED BY public.lot_inventory.id;


--
-- Name: order_items_inbox; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.order_items_inbox (
    id integer NOT NULL,
    order_inbox_id integer NOT NULL,
    sku text NOT NULL,
    sku_lot text,
    quantity integer NOT NULL,
    unit_price_cents integer,
    CONSTRAINT order_items_inbox_quantity_check CHECK ((quantity > 0))
);


ALTER TABLE public.order_items_inbox OWNER TO neondb_owner;

--
-- Name: order_items_inbox_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.order_items_inbox_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_items_inbox_id_seq OWNER TO neondb_owner;

--
-- Name: order_items_inbox_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.order_items_inbox_id_seq OWNED BY public.order_items_inbox.id;


--
-- Name: orders_inbox; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.orders_inbox (
    id integer NOT NULL,
    order_number text NOT NULL,
    order_date date NOT NULL,
    customer_email text,
    status text DEFAULT 'pending'::text NOT NULL,
    shipstation_order_id text,
    total_items integer DEFAULT 0,
    total_amount_cents integer,
    source_system text DEFAULT 'X-Cart'::text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    failure_reason text,
    ship_name text,
    ship_company text,
    ship_street1 text,
    ship_street2 text,
    ship_city text,
    ship_state text,
    ship_postal_code text,
    ship_country text,
    ship_phone text,
    bill_name text,
    bill_company text,
    bill_street1 text,
    bill_street2 text,
    bill_city text,
    bill_state text,
    bill_postal_code text,
    bill_country text,
    bill_phone text,
    shipping_carrier_code text,
    shipping_carrier_id text,
    shipping_service_code text,
    shipping_service_name text,
    tracking_number text,
    CONSTRAINT orders_inbox_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'uploaded'::text, 'awaiting_shipment'::text, 'failed'::text, 'synced_manual'::text, 'shipped'::text, 'cancelled'::text, 'on_hold'::text, 'awaiting_payment'::text])))
);


ALTER TABLE public.orders_inbox OWNER TO neondb_owner;

--
-- Name: orders_inbox_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.orders_inbox_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_inbox_id_seq OWNER TO neondb_owner;

--
-- Name: orders_inbox_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.orders_inbox_id_seq OWNED BY public.orders_inbox.id;


--
-- Name: shipped_items; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.shipped_items (
    id integer NOT NULL,
    ship_date text NOT NULL,
    sku_lot text DEFAULT ''::text NOT NULL,
    base_sku text NOT NULL,
    quantity_shipped integer NOT NULL,
    order_number text,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    tracking_number text,
    CONSTRAINT shipped_items_quantity_shipped_check CHECK ((quantity_shipped > 0))
);


ALTER TABLE public.shipped_items OWNER TO neondb_owner;

--
-- Name: shipped_items_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.shipped_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shipped_items_id_seq OWNER TO neondb_owner;

--
-- Name: shipped_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.shipped_items_id_seq OWNED BY public.shipped_items.id;


--
-- Name: shipped_orders; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.shipped_orders (
    id integer NOT NULL,
    ship_date text NOT NULL,
    order_number text NOT NULL,
    customer_email text,
    total_items integer DEFAULT 0,
    shipstation_order_id text,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    shipping_carrier_code text,
    shipping_carrier_id text,
    shipping_service_code text,
    shipping_service_name text
);


ALTER TABLE public.shipped_orders OWNER TO neondb_owner;

--
-- Name: shipped_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.shipped_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shipped_orders_id_seq OWNER TO neondb_owner;

--
-- Name: shipped_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.shipped_orders_id_seq OWNED BY public.shipped_orders.id;


--
-- Name: shipping_violations; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.shipping_violations (
    id integer NOT NULL,
    order_id integer NOT NULL,
    order_number text NOT NULL,
    violation_type text NOT NULL,
    expected_value text NOT NULL,
    actual_value text,
    detected_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    resolved_at timestamp without time zone,
    is_resolved integer DEFAULT 0 NOT NULL,
    CONSTRAINT shipping_violations_is_resolved_check CHECK ((is_resolved = ANY (ARRAY[0, 1]))),
    CONSTRAINT shipping_violations_violation_type_check CHECK ((violation_type = ANY (ARRAY['hawaiian_service'::text, 'benco_carrier'::text, 'canadian_service'::text])))
);


ALTER TABLE public.shipping_violations OWNER TO neondb_owner;

--
-- Name: shipping_violations_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.shipping_violations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shipping_violations_id_seq OWNER TO neondb_owner;

--
-- Name: shipping_violations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.shipping_violations_id_seq OWNED BY public.shipping_violations.id;


--
-- Name: shipstation_metrics; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.shipstation_metrics (
    id integer NOT NULL,
    metric_name text NOT NULL,
    metric_value integer NOT NULL,
    last_updated text DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.shipstation_metrics OWNER TO neondb_owner;

--
-- Name: shipstation_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.shipstation_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shipstation_metrics_id_seq OWNER TO neondb_owner;

--
-- Name: shipstation_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.shipstation_metrics_id_seq OWNED BY public.shipstation_metrics.id;


--
-- Name: shipstation_order_line_items; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.shipstation_order_line_items (
    id integer NOT NULL,
    order_inbox_id integer NOT NULL,
    sku text NOT NULL,
    shipstation_order_id text NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.shipstation_order_line_items OWNER TO neondb_owner;

--
-- Name: shipstation_order_line_items_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.shipstation_order_line_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shipstation_order_line_items_id_seq OWNER TO neondb_owner;

--
-- Name: shipstation_order_line_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.shipstation_order_line_items_id_seq OWNED BY public.shipstation_order_line_items.id;


--
-- Name: sku_lot; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.sku_lot (
    id integer NOT NULL,
    sku text NOT NULL,
    lot text NOT NULL,
    active integer DEFAULT 1 NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at text DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT sku_lot_active_check CHECK ((active = ANY (ARRAY[0, 1])))
);


ALTER TABLE public.sku_lot OWNER TO neondb_owner;

--
-- Name: sku_lot_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.sku_lot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sku_lot_id_seq OWNER TO neondb_owner;

--
-- Name: sku_lot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.sku_lot_id_seq OWNED BY public.sku_lot.id;


--
-- Name: sync_watermark; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.sync_watermark (
    id integer NOT NULL,
    workflow_name text NOT NULL,
    last_sync_timestamp text NOT NULL,
    updated_at text DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.sync_watermark OWNER TO neondb_owner;

--
-- Name: sync_watermark_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.sync_watermark_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sync_watermark_id_seq OWNER TO neondb_owner;

--
-- Name: sync_watermark_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.sync_watermark_id_seq OWNED BY public.sync_watermark.id;


--
-- Name: system_kpis; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.system_kpis (
    id integer NOT NULL,
    snapshot_date text NOT NULL,
    orders_today integer DEFAULT 0,
    shipments_sent integer DEFAULT 0,
    pending_uploads integer DEFAULT 0,
    system_status text DEFAULT 'online'::text NOT NULL,
    total_revenue_cents integer,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT system_kpis_system_status_check CHECK ((system_status = ANY (ARRAY['online'::text, 'degraded'::text, 'offline'::text])))
);


ALTER TABLE public.system_kpis OWNER TO neondb_owner;

--
-- Name: system_kpis_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.system_kpis_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.system_kpis_id_seq OWNER TO neondb_owner;

--
-- Name: system_kpis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.system_kpis_id_seq OWNED BY public.system_kpis.id;


--
-- Name: weekly_shipped_history; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.weekly_shipped_history (
    id integer NOT NULL,
    start_date text NOT NULL,
    end_date text NOT NULL,
    sku text NOT NULL,
    quantity_shipped integer NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT weekly_shipped_history_quantity_shipped_check CHECK ((quantity_shipped >= 0))
);


ALTER TABLE public.weekly_shipped_history OWNER TO neondb_owner;

--
-- Name: weekly_shipped_history_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.weekly_shipped_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.weekly_shipped_history_id_seq OWNER TO neondb_owner;

--
-- Name: weekly_shipped_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.weekly_shipped_history_id_seq OWNED BY public.weekly_shipped_history.id;


--
-- Name: workflow_controls; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.workflow_controls (
    workflow_name text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_by text DEFAULT 'system'::text,
    last_run_at timestamp without time zone
);


ALTER TABLE public.workflow_controls OWNER TO neondb_owner;

--
-- Name: workflows; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.workflows (
    id integer NOT NULL,
    name text NOT NULL,
    display_name text NOT NULL,
    status text NOT NULL,
    last_run_at text,
    duration_seconds integer,
    records_processed integer,
    details text,
    enabled integer DEFAULT 1 NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    updated_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT workflows_enabled_check CHECK ((enabled = ANY (ARRAY[0, 1]))),
    CONSTRAINT workflows_status_check CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text, 'scheduled'::text])))
);


ALTER TABLE public.workflows OWNER TO neondb_owner;

--
-- Name: workflows_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.workflows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.workflows_id_seq OWNER TO neondb_owner;

--
-- Name: workflows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.workflows_id_seq OWNED BY public.workflows.id;


--
-- Name: bundle_components id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.bundle_components ALTER COLUMN id SET DEFAULT nextval('public.bundle_components_id_seq'::regclass);


--
-- Name: bundle_skus id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.bundle_skus ALTER COLUMN id SET DEFAULT nextval('public.bundle_skus_id_seq'::regclass);


--
-- Name: configuration_params id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.configuration_params ALTER COLUMN id SET DEFAULT nextval('public.configuration_params_id_seq'::regclass);


--
-- Name: inventory_current id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.inventory_current ALTER COLUMN id SET DEFAULT nextval('public.inventory_current_id_seq'::regclass);


--
-- Name: inventory_transactions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.inventory_transactions ALTER COLUMN id SET DEFAULT nextval('public.inventory_transactions_id_seq'::regclass);


--
-- Name: lot_inventory id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lot_inventory ALTER COLUMN id SET DEFAULT nextval('public.lot_inventory_id_seq'::regclass);


--
-- Name: order_items_inbox id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.order_items_inbox ALTER COLUMN id SET DEFAULT nextval('public.order_items_inbox_id_seq'::regclass);


--
-- Name: orders_inbox id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders_inbox ALTER COLUMN id SET DEFAULT nextval('public.orders_inbox_id_seq'::regclass);


--
-- Name: shipped_items id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipped_items ALTER COLUMN id SET DEFAULT nextval('public.shipped_items_id_seq'::regclass);


--
-- Name: shipped_orders id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipped_orders ALTER COLUMN id SET DEFAULT nextval('public.shipped_orders_id_seq'::regclass);


--
-- Name: shipping_violations id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipping_violations ALTER COLUMN id SET DEFAULT nextval('public.shipping_violations_id_seq'::regclass);


--
-- Name: shipstation_metrics id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipstation_metrics ALTER COLUMN id SET DEFAULT nextval('public.shipstation_metrics_id_seq'::regclass);


--
-- Name: shipstation_order_line_items id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipstation_order_line_items ALTER COLUMN id SET DEFAULT nextval('public.shipstation_order_line_items_id_seq'::regclass);


--
-- Name: sku_lot id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sku_lot ALTER COLUMN id SET DEFAULT nextval('public.sku_lot_id_seq'::regclass);


--
-- Name: sync_watermark id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sync_watermark ALTER COLUMN id SET DEFAULT nextval('public.sync_watermark_id_seq'::regclass);


--
-- Name: system_kpis id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.system_kpis ALTER COLUMN id SET DEFAULT nextval('public.system_kpis_id_seq'::regclass);


--
-- Name: weekly_shipped_history id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.weekly_shipped_history ALTER COLUMN id SET DEFAULT nextval('public.weekly_shipped_history_id_seq'::regclass);


--
-- Name: workflows id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.workflows ALTER COLUMN id SET DEFAULT nextval('public.workflows_id_seq'::regclass);


--
-- Data for Name: bundle_components; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.bundle_components (id, bundle_sku_id, component_sku, multiplier, sequence, created_at) FROM stdin;
1	1	17913	1	1	2025-10-02 06:36:51
2	2	17612	40	1	2025-10-02 06:36:51
3	3	17612	15	1	2025-10-02 06:36:51
4	4	17612	6	1	2025-10-02 06:36:51
5	5	17612	1	1	2025-10-02 06:36:51
6	6	17612	1	1	2025-10-02 06:36:51
7	7	17612	41	1	2025-10-02 06:36:51
8	8	17612	16	1	2025-10-02 06:36:51
9	9	17612	1	1	2025-10-02 06:36:51
10	10	17612	1	1	2025-10-02 06:36:51
11	11	17612	50	1	2025-10-02 06:36:51
12	12	17612	18	1	2025-10-02 06:36:51
13	13	17612	7	1	2025-10-02 06:36:51
14	14	17612	45	1	2025-10-02 06:36:51
15	15	17612	18	1	2025-10-02 06:36:51
16	16	17612	9	1	2025-10-02 06:36:51
17	17	17612	45	1	2025-10-02 06:36:51
18	18	17612	18	1	2025-10-02 06:36:51
19	19	17612	9	1	2025-10-02 06:36:51
20	20	17612	3	1	2025-10-02 06:36:51
21	21	17914	40	1	2025-10-02 06:36:51
22	22	17914	15	1	2025-10-02 06:36:51
23	23	17914	6	1	2025-10-02 06:36:51
24	24	17914	1	1	2025-10-02 06:36:51
25	25	17914	1	1	2025-10-02 06:36:51
26	26	17914	1	1	2025-10-02 06:36:51
27	27	17914	16	1	2025-10-02 06:36:51
28	28	17914	41	1	2025-10-02 06:36:51
29	29	17904	40	1	2025-10-02 06:36:51
30	30	17904	15	1	2025-10-02 06:36:51
31	31	17904	6	1	2025-10-02 06:36:51
32	32	17904	1	1	2025-10-02 06:36:51
33	33	17904	1	1	2025-10-02 06:36:51
34	34	17904	1	1	2025-10-02 06:36:51
35	35	17904	16	1	2025-10-02 06:36:51
36	36	17975	40	1	2025-10-02 06:36:51
37	37	17975	15	1	2025-10-02 06:36:51
38	38	17975	6	1	2025-10-02 06:36:51
39	39	17975	1	1	2025-10-02 06:36:51
40	40	17975	1	1	2025-10-02 06:36:51
41	41	17975	41	1	2025-10-02 06:36:51
42	42	17975	16	1	2025-10-02 06:36:51
43	43	18675	40	1	2025-10-02 06:36:51
44	44	18675	15	1	2025-10-02 06:36:51
45	45	18675	6	1	2025-10-02 06:36:51
46	46	18675	41	1	2025-10-02 06:36:51
47	47	18675	16	1	2025-10-02 06:36:51
48	48	18675	1	1	2025-10-02 06:36:51
49	49	18675	1	1	2025-10-02 06:36:51
50	50	17612	4	1	2025-10-02 06:36:51
51	50	17914	1	2	2025-10-02 06:36:51
52	50	17904	1	3	2025-10-02 06:36:51
53	51	17612	4	1	2025-10-02 06:36:51
54	51	17914	1	2	2025-10-02 06:36:51
55	51	17904	1	3	2025-10-02 06:36:51
56	51	17975	1	4	2025-10-02 06:36:51
\.


--
-- Data for Name: bundle_skus; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.bundle_skus (id, bundle_sku, description, active, created_at, updated_at) FROM stdin;
1	18075	OraCare PPR	1	2025-10-02 06:36:51	2025-10-02 06:36:51
2	18225	OraCare Buy 30 Get 8 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
3	18235	OraCare Buy 12 Get 3 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
4	18255	OraCare Buy 5 Get 1 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
5	18345	Autoship; OraCare Health Rinse	1	2025-10-02 06:36:51	2025-10-02 06:36:51
6	18355	Free; OraCare Health Rinse	1	2025-10-02 06:36:51	2025-10-02 06:36:51
7	18185	Webinar Special: OraCare Buy 30 Get 11 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
8	18215	Webinar Special: OraCare Buy 12 Get 4 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
9	18435	OraCare at Grandfathered $219 price	1	2025-10-02 06:36:51	2025-10-02 06:36:51
10	18445	Autoship; FREE Case OraCare Health Rinse	1	2025-10-02 06:36:51	2025-10-02 06:36:51
11	18575	2022 Cyber Monday 30 Get 20 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
12	18585	2022 Cyber Monday 12 Get 6 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
13	18595	2022 Cyber Monday 5 Get 2 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
14	18655	2023 Cyber Monday 30 Get 15 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
15	18645	2023 Cyber Monday 12 Get 6 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
16	18635	2023 Cyber Monday 6 Get 3 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
17	18785	2024 Cyber Monday 30 Get 15 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
18	18775	2024 Cyber Monday 12 Get 6 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
19	18765	2024 Cyber Monday 6 Get 3 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
20	18625	Starter Pack = 3 * 17612	1	2025-10-02 06:36:51	2025-10-02 06:36:51
21	18265	PPR Buy 30 Get 10 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
22	18275	PPR Buy 12 Get 3 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
23	18285	PPR Buy 5 Get 1 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
24	18195	Autoship; OraCare PPR	1	2025-10-02 06:36:51	2025-10-02 06:36:51
25	18375	Free; OraCare PPR	1	2025-10-02 06:36:51	2025-10-02 06:36:51
26	18455	Autoship; FREE OraCare PPR	1	2025-10-02 06:36:51	2025-10-02 06:36:51
27	18495	Webinar Special; PPR Buy 12 Get 4 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
28	18485	Webinar Special; PPR Buy 30 Get 11 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
29	18295	Travel Buy 30 Get 10 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
30	18305	Travel Buy 12 Get 3 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
31	18425	Travel Buy 5 Get 1 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
32	18385	Autoship; OraCare Travel	1	2025-10-02 06:36:51	2025-10-02 06:36:51
33	18395	Free; OraCare Travel	1	2025-10-02 06:36:51	2025-10-02 06:36:51
34	18465	Autoship; FREE OraCare Travel	1	2025-10-02 06:36:51	2025-10-02 06:36:51
35	18515	Webinar Special; Travel Buy 12 Get 4	1	2025-10-02 06:36:51	2025-10-02 06:36:51
36	18315	Reassure Buy 30 Get 10 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
37	18325	Reassure Buy 12 Get 3 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
38	18335	Reassure Buy 5 Get 1 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
39	18405	Autoship; OraCare Reassure	1	2025-10-02 06:36:51	2025-10-02 06:36:51
40	18415	Free; OraCare Reassure	1	2025-10-02 06:36:51	2025-10-02 06:36:51
41	18525	Webinar Special; Reassure Buy 30 Get 11 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
42	18535	Webinar Special; Reassure Buy 12 Get 4	1	2025-10-02 06:36:51	2025-10-02 06:36:51
43	18685	Ortho Protect Buy 30 Get 10 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
44	18695	Ortho Protect Buy 12 Get 3 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
45	18705	Ortho Protect Buy 5 Get 1 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
46	18715	Webinar Special- Buy 30 Get 11 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
47	18725	Webinar Special- Buy 12 Get 4 Free	1	2025-10-02 06:36:51	2025-10-02 06:36:51
48	18735	Autoship- Ortho Protect 1	1	2025-10-02 06:36:51	2025-10-02 06:36:51
49	18745	Autoship- Free Ortho Protect 1	1	2025-10-02 06:36:51	2025-10-02 06:36:51
50	18605	4 cases of 32 oz OraCare Health Rinse, 1 case of 64 oz PPR, 1 case of 2 oz Travel	1	2025-10-02 06:36:51	2025-10-02 06:36:51
51	18615	4 cases of 32 oz OraCare Health Rinse, 1 case Reassure, 1 case of 64 oz PPR, 1 case of 2 oz Travel	1	2025-10-02 06:36:51	2025-10-02 06:36:51
\.


--
-- Data for Name: configuration_params; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.configuration_params (id, category, parameter_name, value, sku, notes, last_updated, created_at) FROM stdin;
1	Rates	pick_pack_rate_cents	68	\N	Pick and pack rate per item in cents	\N	2025-10-01 12:06:14
2	Rates	storage_rate_cents	3	\N	Monthly storage rate per pallet in cents	\N	2025-10-01 12:06:14
3	Rates	monthly_space_rental_cents	30000	\N	Fixed monthly space rental in cents ($300)	\N	2025-10-01 12:06:14
4	PalletConfig	pallet_capacity	156	\N	Cases per pallet	\N	2025-10-01 12:06:14
5	PalletConfig	items_per_case	12	\N	Items per case	\N	2025-10-01 12:06:14
11	System	database_version	1.0	\N	Current database schema version	\N	2025-10-01 12:06:14
12	System	last_migration_date	2025-10-01	\N	Last successful data migration	\N	2025-10-01 12:06:14
13	Rates	OrderCharge	4.25	\N	Charge per unique order	\N	2025-10-01 12:22:30
14	Rates	PackageCharge	0.75	\N	Charge per package (1 SKU = 1 Package)	\N	2025-10-01 12:22:30
15	Rates	SpaceRentalRate	0.45	\N	Daily charge per pallet of space occupied	\N	2025-10-01 12:22:30
16	PalletConfig	PalletCount	48	17612	Units of 17612 per pallet	\N	2025-10-01 12:22:30
17	PalletConfig	PalletCount	81	17904	Units of 17904 per pallet	2025-10-02	2025-10-01 12:22:30
18	PalletConfig	PalletCount	80	17914	Units of 17914 per pallet	\N	2025-10-01 12:22:30
19	PalletConfig	PalletCount	48	18675	Units of 18675 per pallet	\N	2025-10-01 12:22:30
20	PalletConfig	PalletCount	222	18795	Units of 18795 per pallet	\N	2025-10-01 12:22:30
21	InitialInventory	EOD_Prior_Week	1019	17612	1049	\N	2025-10-01 12:22:30
22	InitialInventory	EOD_Prior_Week	468	17904	18	\N	2025-10-01 12:22:30
23	InitialInventory	EOD_Prior_Week	1410	17914	42	\N	2025-10-01 12:22:30
24	InitialInventory	EOD_Prior_Week	714	18675	715	\N	2025-10-01 12:22:30
25	InitialInventory	EOD_Prior_Week	7719	18795	7780	\N	2025-10-01 12:22:30
26	Key Products	PT Kit	 	17612	 	\N	2025-10-01 12:22:30
27	Key Products	Travel Kit	 	17904	 	\N	2025-10-01 12:22:30
28	Key Products	PPR Kit	 	17914	 	\N	2025-10-01 12:22:30
29	Key Products	Ortho Protect	 	18675	 	\N	2025-10-01 12:22:30
30	Key Products	OraPro Paste Peppermint	None	18795	\N	\N	2025-10-01 12:22:30
31	Reporting	CurrentMonthlyReportYear	2025	\N	\N	\N	2025-10-01 12:22:30
32	Reporting	CurrentMonthlyReportMonth	9	\N	\N	\N	2025-10-01 12:22:30
33	Reporting	CurrentWeeklyReportStartDate	9/22/2025	\N	\N	\N	2025-10-01 12:22:30
34	Reporting	CurrentWeeklyReportEndDate	9/28/2025	\N	\N	\N	2025-10-01 12:22:30
35	Inventory	EomPreviousMonth	1493	17612	\N	\N	2025-10-01 12:22:30
36	Inventory	EomPreviousMonth	59	17904	\N	\N	2025-10-01 12:22:30
37	Inventory	EomPreviousMonth	127	17914	\N	\N	2025-10-01 12:22:30
38	Inventory	EomPreviousMonth	738	18675	\N	\N	2025-10-01 12:22:30
39	Inventory	EomPreviousMonth	7799	18795	\N	\N	2025-10-01 12:22:30
40	ShipStation Product Mapping	17612	Oracare 16oz	\N	\N	\N	2025-10-01 12:22:30
41	ShipStation Product Mapping	17904	Oracare Travel Kit	\N	\N	\N	2025-10-01 12:22:30
42	ShipStation Product Mapping	17914	Oracare 32oz	\N	\N	\N	2025-10-01 12:22:30
43	ShipStation Product Mapping	18675	Ortho Protect	\N	\N	\N	2025-10-01 12:22:30
44	ShipStation Product Mapping	18795	OraPro Paste Peppermint	\N	\N	\N	2025-10-01 12:22:30
50	SKU_Lot	18675	240231	18675	\N	2025-10-02	2025-10-02 07:34:45
51	SKU_Lot	18795	11001	18795	\N	2025-10-02	2025-10-02 07:34:45
52	SKU_Lot	17612	250237	17612	\N	2025-10-02	2025-10-02 07:34:45
53	SKU_Lot	17914	250297	17914	\N	2025-10-02	2025-10-02 07:34:45
54	SKU_Lot	17904	250240	17904	\N	2025-10-02	2025-10-02 07:34:45
55	Product Names	17612	Oracare 16oz	17612	\N	\N	2025-10-02 09:25:45
56	Product Names	17904	Oracare Travel Kit	17904	\N	\N	2025-10-02 09:25:45
57	Product Names	17914	Oracare 32oz	17914	\N	\N	2025-10-02 09:25:45
58	Product Names	18675	Ortho Protect	18675	\N	\N	2025-10-02 09:25:45
59	Product Names	18795	OraPro Paste Peppermint	18795	\N	\N	2025-10-02 09:25:45
\.


--
-- Data for Name: inventory_current; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.inventory_current (id, sku, product_name, current_quantity, weekly_avg_cents, alert_level, reorder_point, last_updated) FROM stdin;
1	17612	 	731	48000	normal	50	2025-10-15 21:28:37.337628+00
3	17904	 	419	1300	normal	50	2025-10-15 21:28:37.337628+00
2	17914	 	1326	2800	normal	50	2025-10-15 21:28:37.337628+00
5	18675	 	713	400	normal	50	2025-10-15 21:28:37.337628+00
10	18795	None	7681	200	normal	50	2025-10-15 21:28:37.337628+00
\.


--
-- Data for Name: inventory_transactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.inventory_transactions (id, date, sku, quantity, transaction_type, notes, created_at) FROM stdin;
1	2025-05-16	17612	528	Receive	Unknown	2025-10-01 12:22:30
2	2025-05-20	17612	576	Receive	\N	2025-10-01 12:22:30
3	2025-05-25	17612	576	Receive	\N	2025-10-01 12:22:30
4	2025-05-02	17612	382	Receive	\N	2025-10-01 12:22:30
5	2025-06-18	17612	576	Receive	250172	2025-10-01 12:22:30
6	2025-06-23	17612	376	Receive	250172	2025-10-01 12:22:30
7	2025-06-04	17612	478	Receive	250101	2025-10-01 12:22:30
8	2025-07-01	17612	576	Receive	250195	2025-10-01 12:22:30
9	2025-07-03	17612	576	Receive	250195	2025-10-01 12:22:30
10	2025-07-09	17612	576	Receive	250195	2025-10-01 12:22:30
11	2025-07-09	18795	933	Receive	11001	2025-10-01 12:22:30
12	2025-07-09	18795	935	Receive	11002	2025-10-01 12:22:30
13	2025-07-09	18795	1018	Receive	11003	2025-10-01 12:22:30
14	2025-07-09	18795	1034	Receive	11004	2025-10-01 12:22:30
15	2025-07-09	18795	556	Receive	11005	2025-10-01 12:22:30
16	2025-07-09	18795	996	Receive	11006	2025-10-01 12:22:30
17	2025-07-09	18795	766	Receive	11007	2025-10-01 12:22:30
18	2025-07-11	17612	426	Receive	250195	2025-10-01 12:22:30
19	2025-07-16	18795	996	Receive	11008	2025-10-01 12:22:30
20	2025-07-16	18795	594	Receive	11009	2025-10-01 12:22:30
23	2025-07-30	17612	576	Receive	250216	2025-10-01 12:22:30
24	2025-07-31	17612	576	Receive	250216	2025-10-01 12:22:30
25	2025-08-05	17612	576	Receive	250216	2025-10-01 12:22:30
26	2025-08-12	17612	430	Receive	250216	2025-10-01 12:22:30
27	2025-08-27	17612	576	Receive	250237	2025-10-01 12:22:30
29	2025-08-29	17612	432	Receive	250237	2025-10-01 12:22:30
30	2025-09-10	17612	384	Receive	250237	2025-10-01 12:22:30
31	2025-09-12	17914	680	Receive	250297	2025-10-01 12:22:30
36	2025-05-12	17612	5	Repack	\N	2025-10-01 21:18:27
37	2025-05-12	17612	2	Repack	\N	2025-10-01 21:18:27
38	2025-05-12	17914	14	Repack	\N	2025-10-01 21:18:27
53	2025-07-11	17612	9	Repack	250101	2025-10-01 21:18:27
63	2025-09-03	17914	6	Repack	240286	2025-10-01 21:18:27
64	2025-09-03	17612	4	Repack	250195	2025-10-01 21:18:27
67	2025-09-18	17914	860	Receive	250297	2025-10-01 21:35:29
68	2025-10-01	17612	6	Adjust Down	Lot 250237 shipped via UPS	2025-10-02 16:04:19
69	2025-10-01	18795	1	Adjust Down	Shipped UPS	2025-10-02 16:23:52
70	2025-10-03	17612	576	Receive	250300	2025-10-03 20:18:27
71	2025-10-03	17612	3	Adjust Down	EOW physical count	2025-10-03 20:22:30
73	2025-10-08	17612	576	Receive	250300	2025-10-10 20:17:09
75	2025-10-13	17612	576	Receive	250300	2025-10-15 21:07:50.67628+00
\.


--
-- Data for Name: lot_inventory; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.lot_inventory (id, sku, lot, initial_qty, manual_adjustment, received_date, status, notes, created_at, updated_at) FROM stdin;
1	17612	250237	1019	0	2025-09-19	active	Imported from 9/19/2025 baseline inventory (EOD Prior Week)	2025-10-06 16:58:45	2025-10-06 16:58:45
2	17904	250240	468	0	2025-09-19	active	Imported from 9/19/2025 baseline inventory (EOD Prior Week)	2025-10-06 16:58:45	2025-10-06 16:58:45
3	17914	250297	1410	0	2025-09-19	active	Imported from 9/19/2025 baseline inventory (EOD Prior Week)	2025-10-06 16:58:45	2025-10-06 16:58:45
4	18675	240231	714	0	2025-09-19	active	Imported from 9/19/2025 baseline inventory (EOD Prior Week)	2025-10-06 16:58:45	2025-10-06 16:58:45
5	18795	11001	7719	0	2025-09-19	active	Imported from 9/19/2025 baseline inventory (EOD Prior Week)	2025-10-06 16:58:45	2025-10-06 16:58:45
\.


--
-- Data for Name: order_items_inbox; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.order_items_inbox (id, order_inbox_id, sku, sku_lot, quantity, unit_price_cents) FROM stdin;
4749	441	17914	\N	1	\N
5039	633	17914	17914 - 250297	2	0
5040	634	17612	17612 - 250070	2	0
2501	414	17612	\N	1	\N
3052	416	17904	\N	1	\N
9389	442	17612	\N	1	\N
9390	442	17904	\N	1	\N
33298	443	17612	\N	6	\N
34483	444	17612	\N	1	\N
43457	448	17612	\N	15	\N
511	408	17612	\N	1	\N
512	409	17612	\N	1	\N
513	410	17612	\N	15	\N
514	411	17904	\N	1	\N
515	412	17612	\N	6	\N
516	413	17914	\N	1	\N
2640	415	17612	\N	3	\N
3189	417	17612	\N	15	\N
3190	418	17612	\N	1	\N
3191	419	17612	\N	1	\N
4605	420	17612	\N	1	\N
4606	421	17612	\N	15	\N
4607	439	17612	\N	4	\N
4608	440	17612	\N	1	\N
4894	441	17914	\N	1	\N
43606	448	17612	\N	15	\N
43607	449	17612	\N	15	\N
43608	450	17612	\N	1	\N
43609	450	17904	\N	1	\N
43610	451	17612	\N	6	\N
43611	451	17914	\N	1	\N
43612	451	17904	\N	1	\N
43613	452	17612	\N	3	\N
43614	453	17612	\N	6	\N
43615	453	18795	\N	1	\N
43616	454	17612	\N	6	\N
42713	445	18795	\N	1	\N
42714	445	17612	\N	1	\N
43617	455	17612	\N	6	\N
43618	456	17612	\N	1	\N
43619	457	17904	\N	1	\N
43620	458	17612	\N	1	\N
43621	459	17612	\N	6	\N
43622	460	17612	\N	6	\N
43623	461	17612	\N	1	\N
43624	462	17612	\N	15	\N
43625	463	17612	\N	6	\N
43626	464	17612	\N	2	\N
43627	465	17612	\N	3	\N
43628	466	17612	\N	1	\N
43629	467	18795	\N	2	\N
43630	468	17612	\N	6	\N
43631	469	17612	\N	1	\N
43632	470	17612	\N	6	\N
43633	471	17612	\N	6	\N
43634	472	17612	\N	2	\N
43635	474	17612	\N	1	\N
43636	475	17612	\N	6	\N
43637	476	17612	\N	1	\N
43638	477	17612	\N	2	\N
43639	477	17904	\N	1	\N
43640	478	17612	\N	1	\N
43641	479	17612	\N	1	\N
43642	480	17612	\N	1	\N
43643	481	17612	\N	1	\N
43644	482	17612	\N	40	\N
43645	483	17612	\N	2	\N
43646	484	17612	\N	6	\N
43647	485	17612	\N	6	\N
43648	486	17612	\N	6	\N
43649	487	17612	\N	6	\N
43650	488	17612	\N	15	\N
43651	489	17612	\N	1	\N
43652	490	17612	\N	2	\N
43653	491	17612	\N	1	\N
43654	494	18795	\N	1	\N
43655	495	17612	\N	40	\N
43656	496	17904	\N	6	\N
43657	496	17612	\N	1	\N
43658	497	17612	\N	1	\N
43659	497	17904	\N	1	\N
43660	498	17914	\N	1	\N
43661	499	17612	\N	2	\N
43662	500	17612	\N	6	\N
43663	501	17612	\N	6	\N
43664	502	17612	\N	1	\N
43665	544	18795	\N	1	\N
43666	545	17612	\N	2	\N
43667	546	17612	\N	3	\N
43668	547	17612	\N	2	\N
43669	548	17612	\N	1	\N
43670	549	17612	\N	1	\N
43671	550	17612	\N	1	\N
43672	551	17612	\N	3	\N
43673	552	17612	\N	1	\N
43674	553	17612	\N	1	\N
43675	554	17612	\N	2	\N
43676	555	17612	\N	1	\N
43677	556	17612	\N	1	\N
43678	557	17612	\N	1	\N
43679	558	17612	\N	1	\N
43680	559	17612	\N	1	\N
43681	560	17612	\N	2	\N
43682	561	17612	\N	2	\N
43683	562	17612	\N	3	\N
43684	563	17612	\N	1	\N
43685	564	17612	\N	6	\N
43686	565	17612	\N	3	\N
43687	566	17612	\N	2	\N
43688	567	17612	\N	5	\N
43689	568	17612	\N	2	\N
43690	569	17612	\N	3	\N
43691	570	17612	\N	7	\N
43692	571	17612	\N	1	\N
43693	572	17612	\N	1	\N
43694	573	17612	\N	1	\N
43695	574	17612	\N	2	\N
43696	575	17612	\N	4	\N
43697	576	17612	\N	2	\N
43698	577	17612	\N	6	\N
43699	578	17612	\N	2	\N
43700	579	17612	\N	4	\N
43701	580	17612	\N	2	\N
43702	581	17612	\N	3	\N
43703	582	17612	\N	2	\N
43704	583	17612	\N	10	\N
43705	584	17612	\N	1	\N
43706	585	17612	\N	5	\N
43707	586	17612	\N	5	\N
43708	587	17612	\N	4	\N
43709	587	17914	\N	1	\N
43710	588	17612	\N	1	\N
43711	589	17612	\N	1	\N
43712	590	17612	\N	5	\N
43713	591	17612	\N	1	\N
43714	592	17612	\N	1	\N
43715	593	17612	\N	8	\N
43716	594	17612	\N	5	\N
43717	595	17612	\N	10	\N
43718	595	17914	\N	1	\N
43719	596	17612	\N	1	\N
43720	597	17612	\N	4	\N
43721	598	17612	\N	1	\N
43722	599	17612	\N	5	\N
43723	599	17904	\N	1	\N
43724	600	17612	\N	2	\N
43725	601	17612	\N	3	\N
43726	602	17904	\N	1	\N
43727	603	17612	\N	2	\N
43728	604	17612	\N	6	\N
43729	605	17612	\N	2	\N
43730	606	17612	\N	1	\N
43731	607	17914	\N	3	\N
43732	608	17612	\N	1	\N
43733	609	17612	\N	1	\N
43734	610	17612	\N	6	\N
43735	611	17612	\N	1	\N
43736	625	17612	\N	1	\N
43737	626	17612	\N	6	\N
43738	627	17612	\N	3	\N
43739	628	17914	\N	2	\N
43740	629	17904	\N	2	\N
43741	630	17612	\N	3	\N
43742	631	17612	\N	6	\N
43743	632	17612	\N	2	\N
43744	635	17612	\N	6	\N
43745	636	17612	\N	1	\N
43746	637	17612	\N	1	\N
43747	638	17612	\N	1	\N
43748	639	17612	\N	1	\N
43749	640	17612	\N	6	\N
43750	641	17612	\N	1	\N
43751	642	17612	\N	15	\N
43752	643	17904	\N	1	\N
43753	644	17612	\N	2	\N
43754	645	17612	\N	2	\N
\.


--
-- Data for Name: orders_inbox; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.orders_inbox (id, order_number, order_date, customer_email, status, shipstation_order_id, total_items, total_amount_cents, source_system, created_at, updated_at, failure_reason, ship_name, ship_company, ship_street1, ship_street2, ship_city, ship_state, ship_postal_code, ship_country, ship_phone, bill_name, bill_company, bill_street1, bill_street2, bill_city, bill_state, bill_postal_code, bill_country, bill_phone, shipping_carrier_code, shipping_carrier_id, shipping_service_code, shipping_service_name, tracking_number) FROM stdin;
1	686545	2025-09-27	frontdesk@dentaldesignbg.com	shipped	220517780	3	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Sue Palatore	Dental Design	1151 N Arlington Heights Rd	\N	Buffalo Grove	IL	60089	US	(847) 459-4330	Sue Palatore	Dental Design	1151 N Arlington Heights Rd	\N	Buffalo Grove	IL	60089	US	(847) 459-4330	fedex	556346	fedex_ground	FedEx Ground	\N
2	686555	2025-09-27	maryemazurek@gmail.com	shipped	220517782	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Janice Mazurek	Janice Mazurek DDS	379 court Ave	\N	Ventura	CA	93003	US	8057466888	Janice Mazurek	Janice Mazurek DDS	379 court Ave	\N	Ventura	CA	93003	US	8057466888	fedex	556346	fedex_ground	FedEx Ground	\N
3	686575	2025-09-29	office@sacramentoriverdentalgroup.com	shipped	220525848	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Ashkan Alizadeh	Sacramento River Dental Group	905 Secret River Dr.\nSte C	\N	Sacramento	CA	95831	US	9163914848	Ashkan Alizadeh	Sacramento River Dental Group	905 Secret River Dr.\nSte C	\N	Sacramento	CA	95831	US	(916) 391-4848	fedex	556346	fedex_ground	FedEx Ground	\N
4	686585	2025-09-29	info@glacialsandsoms.com	shipped	220538591	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Sonia Bennett	Glacial Sands oral, facial, implant surgery	1008 Broadway Ave	\N	Chesterton	IN	46304	US	(219) 964-4321	Sonia Bennett	Glacial Sands oral, facial, implant surgery	1008 Broadway Ave	\N	Chesterton	IN	46304	US	(219) 964-4321	fedex	556346	fedex_ground	FedEx Ground	\N
5	686595	2025-09-29	Toothfairy2@live.com	shipped	220541848	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Gwendolyn Buck	Northern Trails Dental Care	271 E. M-35	\N	Gwinn	MI	49841	US	(906) 346-6349	Gwendolyn Buck	Northern Trails Dental Care	271 E. M-35	\N	Gwinn	MI	49841	US	(906) 346-6349	fedex	556346	fedex_ground	FedEx Ground	\N
6	686605	2025-09-29	katy@lhdmpls.com	shipped	220545596	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Katy Pilcher	Linden Hills Dentistry	4289 Sheridan Ave S.	\N	Minneapolis	MN	55410	US	(612) 922-6164	Katy Pilcher	Linden Hills Dentistry	4289 Sheridan Ave S.	\N	Minneapolis	MN	55410	US	(612) 922-6164	fedex	556346	fedex_ground	FedEx Ground	\N
7	686615	2025-09-29	ravikumarr@pacden.com	cancelled	220549674	3	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 06:31:07	\N	RAKSHITH ARAKOTARAM RAVIKUMAR	Bastrop Modern Dentistry	1670 HWY 71 E, STE A	\N	BASTROP	TX	78602	US	(512) 240-6496	RAKSHITH ARAKOTARAM RAVIKUMAR	Bastrop Modern Dentistry	1670 HWY 71 E, STE A	\N	BASTROP	TX	78602	US	(512) 240-6496	fedex	556346	fedex_ground	FedEx Ground	\N
8	686625	2025-09-29	marie.alston@pacden.com	cancelled	220549676	15	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 06:31:07	\N	Marie Alston	Stevens Ranch Dental	14314 Potranco Rd	\N	San Antonio	TX	78245	US	(830) 219-1378	Marie Alston	Stevens Ranch Dental	14314 Potranco Rd	\N	San Antonio	TX	78245	US	(830) 219-1378	fedex	556346	fedex_ground	FedEx Ground	\N
9	686635	2025-09-29	admin@blueriverdental.com	shipped	220562441	15	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Cassie Vanosdol	Blue River Dental	1818 N Riley Hwy	\N	Shelbyville	IN	46176	US	(317) 392-1468	Cassie Vanosdol	Blue River Dental	1818 N Riley Hwy	\N	Shelbyville	IN	46176	US	(317) 392-1468	fedex	556346	fedex_ground	FedEx Ground	\N
10	686645	2025-09-29	amandaolson620@gmail.com	shipped	220579521	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Dr. Amanda Dibble	Dibble Family Dental	33801 First Way South\nSuite 201	\N	Federal Way	WA	98003	US	(253) 838-4770	Dr. Amanda Dibble	Dibble Family Dental	33801 First Way South\nSuite 201	\N	Federal Way	WA	98003	US	(253) 838-4770	fedex	556346	fedex_ground	FedEx Ground	\N
11	686655	2025-09-29	rocklandpediatricdental@gmail.com	shipped	220589402	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Anne Chaly	Rockland Pediatric Dental	238 North Main St.	\N	New City	NY	10956	US	(845) 634-8900	Anne Chaly	Rockland Pediatric Dental	238 North Main St.	\N	New City	NY	10956	US	(845) 634-8900	fedex	556346	fedex_ground	FedEx Ground	\N
12	686665	2025-09-29	4evolutiondentistry@gmail.com	shipped	220589405	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Mohamad El-Kheir	Evolution at Tanglewood Dental	5793 San Felipe St	\N	Houston	TX	77057	US	(713) 647-8000	Mohamad El-Kheir	Evolution at Tanglewood Dental	5793 San Felipe St	\N	Houston	TX	77057	US	(713) 647-8000	fedex	556346	fedex_ground	FedEx Ground	\N
13	686675	2025-09-29	dds4yl@gmail.com	shipped	220594167	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Edward Barragan	E. R. Barragan Dental Corp	18276 Imperial Hwy	\N	Yorba Linda	CA	92886	US	(714) 993-7910	Edward Barragan	E. R. Barragan Dental Corp	18276 Imperial Hwy	\N	Yorba Linda	CA	92886	US	(714) 993-7910	fedex	556346	fedex_ground	FedEx Ground	\N
14	686685	2025-09-29	prosupplies@heartland.com	shipped	220595662	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	TFD - Clinton Township TFD - Clinton Township	TFD - Clinton Township	37450 Garfield Rd #100	\N	Clinton TWP	MI	48036	US	5862869060	Heartland Dental	Heartland Dental	1200 Network Centre Dr	\N	Effingham	IL	62401	US	2175405100	fedex	556346	fedex_ground	FedEx Ground	\N
15	686695	2025-09-29	flossn_2000@yahoo.com	shipped	220597061	15	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Gordon Fraser	Conyers Denture and Implant Center	1916 Iris Dr., S.W.	\N	Conyers	GA	30094	US	(770) 483-4469	Gordon Fraser	Conyers Denture and Implant Center	Po box 2213	\N	Peachtree City	GA	30269	US	7704834469	fedex	556346	fedex_ground	FedEx Ground	\N
16	686705	2025-09-29	Office@stonestreetdental.com	shipped	220615990	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-03 17:42:12	\N	Alison Garrad	Stone Street Dental	4613 Stonewall Street	\N	Greenville	TX	75401	US	(903) 455-6075	Alison Garrad	Stone Street Dental	4613 Stonewall Street	\N	Greenville	TX	75401	US	(903) 455-6075	fedex	556346	fedex_ground	FedEx Ground	\N
17	686715	2025-09-29	oliver1darian1@aol.com	shipped	220629517	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Dr. Jack Lazer	Dr. Jack Lazer	105 McCourt Place	\N	Johnstown	PA	15904	US	8142694404	Dr. Jack Lazer	Dr. Jack Lazer	105 McCourt Place	\N	Johnstown	PA	15904	US	8142694404	fedex	556346	fedex_ground	FedEx Ground	\N
19	686735	2025-09-29	info@pensacoladentistry.com	shipped	220648018	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	William Rolfe	Coastal Cosmetic and Family Dentistry	6160 N Davis Hwy\nSte 6	\N	Pensacola	FL	32504	US	(850) 479-3355	William Rolfe	Coastal Cosmetic and Family Dentistry	6160 N Davis Hwy\nSte 6	\N	Pensacola	FL	32504	US	(850) 479-3355	fedex	556346	fedex_ground	FedEx Ground	\N
20	686745	2025-09-29	jeremylansford10@yahoo.com	shipped	220652163	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Jeremy Lansford	Lansford Dental Corporation	1134 Vine Street	\N	Paso Robles	CA	93446	US	(805) 238-1441	Jeremy Lansford	Lansford Dental Corporation	1134 Vine Street	\N	Paso Robles	CA	93446	US	(805) 238-1441	fedex	556346	fedex_ground	FedEx Ground	\N
21	686755	2025-09-29	officemanager@moderndentalgroup.com	shipped	220662704	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Shawn Casella	Modern Dental Group	333 state street \nste 310	\N	Erie	PA	16507	US	(814) 456-0710	Shawn Casella	Modern Dental Group	333 state street \nste 310	\N	Erie	PA	16507	US	(814) 456-0710	fedex	556346	fedex_ground	FedEx Ground	\N
22	686765	2025-09-29	info@bethesda-dental.com	shipped	220671185	2	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Amma Boateng	Amma Boateng DMD LLA	4830 Cordell Ave	\N	BETHESDA	MD	20814	US	(267) 368-1259	Amma Boateng	Amma Boateng DMD LLA	4830 Cordell Ave	\N	BETHESDA	MD	20814	US	(267) 368-1259	fedex	556346	fedex_ground	FedEx Ground	\N
613	100527	2025-10-09	\N	shipped	225073031	0	\N	X-Cart	2025-10-15 17:16:49.64425	2025-10-15 17:58:04.892279	20251015_175428_141954	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
23	686775	2025-09-29	leadership@brantlydental.com	shipped	220690241	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Chad Brantly	Brantly Dental	2149 Office Park Drive	\N	San Angelo	TX	76904	US	325-949-9668	Chad Brantly	Brantly Dental	2149 Office Park Drive	\N	San Angelo	TX	76904	US	325-949-9668	fedex	556346	fedex_ground	FedEx Ground	\N
24	686785	2025-09-29	ordering@salinasdds.com	shipped	220836879	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Steven Ross	Ross Family Dental	750 E. Romie Lane, Ste. A	\N	Salinas	CA	93901	US	(831) 422-5351	Steven Ross	Ross Family Dental	750 E Romie Lane\nSte A	\N	Salinas	CA	93901	US	(831) 422-5351	fedex	556346	fedex_ground	FedEx Ground	\N
25	686795	2025-09-29	summitviewdentalut@gmail.com	shipped	220836880	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Whitnee Moreland	Summit View Dental	445 E 4500 S #150	\N	Millcreek	UT	84107	US	(801) 561-0061	Whitnee Moreland	Summit View Dental	445 E 4500 S #150	\N	Millcreek	UT	84107	US	(801) 561-0061	fedex	556346	fedex_ground	FedEx Ground	\N
26	686805	2025-09-30	vendors@bryantstdental.com	shipped	220836881	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Chad Abed	Bryant St Dental	824 Bryant St	\N	Palo Alto	CA	94301	US	(650) 327-1787	Chad Abed	Bryant St Dental	824 Bryant St	\N	Palo Alto	CA	94301	US	(650) 327-1787	fedex	556346	fedex_ground	FedEx Ground	\N
27	686815	2025-09-30	Cjpaulsondds@gmail.com	shipped	220836882	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Chris Paulson	Arbor Dental Associates	44170 w. 12 mile\nSte.200	\N	Novi	MI	48377	US	(248) 553-9393	Chris Paulson	Arbor Dental Associates	44170 w. 12 mile\nSte.200	\N	Novi	MI	48377	US	(248) 553-9393	fedex	556346	fedex_ground	FedEx Ground	\N
28	686825	2025-09-30	dwoods@restoredental.com	shipped	220848780	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Dustin Woods	Restore Dental	3301 S Walton Blvd\nSte 19	\N	Bentonville	AR	72712	US	(479) 259-9060	Dustin Woods	Restore Dental	3301 S Walton Blvd\nSte 19	\N	Bentonville	AR	72712	US	(479) 259-9060	fedex	556346	fedex_ground	FedEx Ground	\N
29	686845	2025-09-30	vendors@mirandaandortegadental.com	shipped	220852454	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Alex Miranda	Drs. Miranda and Ortega DMD	1298 N Dixie Hwy \n#1	\N	New Smyrna Beach	FL	32168	US	(386) 428-2958	Alex Miranda	Drs. Miranda and Ortega DMD	1298 N Dixie Hwy \n#1	\N	New Smyrna Beach	FL	32168	US	(386) 428-2958	fedex	556346	fedex_ground	FedEx Ground	\N
32	686875	2025-09-30	kristin@wilmarmanagement.com	shipped	220863693	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Mikkah Waggamon	Residential	401 Forest Brook Drive	\N	Saint Albans	WV	25177	US	304-931-1135	Mikkah Waggamon	Residential	401 Forest Brook Drive	\N	Saint Albans	WV	25177	US	304-931-1135	fedex	556346	fedex_home_delivery	FedEx Home Delivery	\N
33	686895	2025-09-30	dentalgooden@gmail.com	shipped	220878880	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Barry Gooden	Barry F. Gooden D.D.S.P.A.	122 Medical Drive	\N	Boerne	TX	78006	US	(830) 249-8559	Barry Gooden	Barry F. Gooden D.D.S.P.A.	122 Medical Drive	\N	Boerne	TX	78006	US	(830) 249-8559	fedex	556346	fedex_ground	FedEx Ground	\N
34	686905	2025-09-30	fcsmilesdrp@gmail.com	shipped	220910954	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-07 23:37:00	\N	Niral Patel	Fountain City Smiles	2944 Tazewell Pike\nSuite 2	\N	Knoxville	TN	37918	US	(860) 938-1745	Niral Patel	Fountain City Smiles	2944 Tazewell Pike\nSuite 2	\N	Knoxville	TN	37918	US	(860) 938-1745	fedex	556346	fedex_ground	FedEx Ground	\N
437	100522	2025-10-09	armenrai@yahoo.com	cancelled	225067367	1	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 17:58:04.892279	\N	Aparna Menami	APARNA MENRAI, DDS	6541 CROWN BLVD STE A	\N	SAN JOSE	CA	95120-2907	US	(408) 226-3870	Aparna Menami	\N	6541 Crown BLVD\nSuite A	\N	San Jose	CA	95120	US	\N	fedex	556346	fedex_ground	FedEx Ground	\N
438	100523	2025-10-09	info@matthewcripedds.com	cancelled	225067375	2	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 17:58:04.892279	\N	MATTHEW CRIPE	DR. MATTHEW CRIPE	303 HAMILTON ST	\N	DOWAGIAC	MI	49047-1259	US	2697825511	MATTHEW CRIPE	\N	303 Hamilton Street	\N	Dowagiac	MI	49047	US	\N	fedex	556346	fedex_ground	FedEx Ground	\N
614	100528	2025-10-09	\N	shipped	225073041	0	\N	X-Cart	2025-10-15 17:16:50.660234	2025-10-15 17:58:04.892279	20251015_175428_141954	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
455	689565	2025-10-13	office@charlottedentalarts.com	shipped	224351402	6	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Edwin Porter	Charlotte Dental Arts	3135 Springbank Ln\nSte 150	\N	CHARLOTTE	NC	28226	US	(704) 544-5330	Edwin Porter	Charlotte Dental Arts	3135 Springbank Ln\nSte 150	\N	CHARLOTTE	NC	28226	US	(704) 544-5330	fedex	556346	fedex_ground	FedEx Ground	\N
475	689785	2025-10-13	info@drogata.com	shipped	224504368	6	\N	X-Cart	2025-10-13 19:54:08	2025-10-16 17:27:39.325556	\N	Lance Ogata	Dr. Lance Ogata- TB	140 Hoohana Steet\nSuite 301	\N	Kahului	HI	96732	US	1-808-877-8090	Lance Ogata	Dr. Lance Ogata- TB	140 Hoohana Steet\nSuite 301	\N	Kahului	HI	96732	US	1-808-877-8090	fedex	556346	fedex_2day	FedEx 2Day	\N
627	690885	2025-10-15	drsaab@houstondentistry.com	shipped	225095066	3	\N	X-Cart	2025-10-15 18:06:26.449834	2025-10-16 17:27:39.325556	\N	Dealla Saab	Houston Dentistry at Memorial	2450 Fondren Rd\n250	\N	Houston	TX	77063	US	(713) 789-4300	Dealla Saab	Houston Dentistry at Memorial	2450 Fondren Rd\n250	\N	Houston	TX	77063	US	(713) 789-4300	fedex	556346	fedex_ground	FedEx Ground	\N
629	690905	2025-10-15	info@manyakdental.com	shipped	225115317	2	\N	X-Cart	2025-10-15 21:11:06.712059	2025-10-16 17:27:39.325556	\N	Tanya Manyak	Manyak Dental Group- TB	100 South Ellsworth Ave\nSuite #601	\N	San Mateo	CA	94401	US	(650) 342-9941	Tanya Manyak	Manyak Dental Group- TB	100 South Ellsworth Ave\nSuite #601	\N	San Mateo	CA	94401	US	(650) 342-9941	fedex	556346	fedex_ground	FedEx Ground	\N
587	690595	2025-10-15	office@thewestgatedental.com	shipped	225060656	5	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Richard DiSimoni	West Gate Family Dentistry	3381 W Main St\n#3	\N	St. Charles	IL	60175	US	(630) 513-2121	Richard DiSimoni	West Gate Family Dentistry	3381 W Main St\n#3	\N	St. Charles	IL	60175	US	(630) 513-2121	fedex	556346	fedex_ground	FedEx Ground	\N
588	690605	2025-10-15	owen.dentistry@yahoo.com	shipped	225005542	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	MARGARET ZIMMER	OWEN FAMILY DENTISTRY, L.L.C.	7 PITNEY STREET	\N	Sayre	PA	18840	US	5708882494	MARGARET ZIMMER	OWEN FAMILY DENTISTRY, L.L.C.	619 Sturdevent road	\N	Gillett	PA	16925	US	(570) 888-2494	fedex	556346	fedex_ground	FedEx Ground	\N
592	690645	2025-10-15	arwtx2@wdbdentalhealth.com	shipped	225006633	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Jennifer Adams	Dr. Alan Weinstein	7835 remington Rd	\N	Cincinnati	OH	45242	US	(513) 793-1977	Jennifer Adams	Dr. Alan Weinstein	7835 remington Rd	\N	Cincinnati	OH	45242	US	(513) 793-1977	fedex	556346	fedex_ground	FedEx Ground	\N
593	690655	2025-10-15	brittany@mcfdental.com	shipped	225006636	8	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Brittany DePriest	Monroe County Family Dental	857 S Auto Mall Rd Ste 4	\N	Bloomington	IN	47401	US	(812) 339-4400	Brittany DePriest	Monroe County Family Dental	857 S Auto Mall Rd Ste 4	\N	Bloomington	IN	47401	US	(812) 339-4400	fedex	556346	fedex_ground	FedEx Ground	\N
595	690675	2025-10-15	melissagoodpaster@gmail.com	shipped	225060528	11	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Melissa Goodpaster	Cherry Creek Dental Spa	155 S. Madison Street\nste 220	\N	Denver	CO	80209	US	(303) 835-0033	Melissa Goodpaster	Cherry Creek Dental Spa	155 S. Madison Street\nste 220	\N	Denver	CO	80209	US	(303) 835-0033	fedex	556346	fedex_ground	FedEx Ground	\N
596	690685	2025-10-15	officemanager@perkinsdental.com	shipped	225006644	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Thomas Perkins	Perkins Dental Associates	101 Bradford Road Suite 270	\N	Wexford	PA	15090	US	(724) 935-4210	Thomas Perkins	Perkins Dental Associates	101 Bradford Road Suite 270	\N	Wexford	PA	15090	US	(724) 935-4210	fedex	556346	fedex_ground	FedEx Ground	\N
597	690695	2025-10-15	angela_rutherforddds@yahoo.com	shipped	225006651	4	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Robin Rutherford	The Art of Dentistry	4712 E. University Blvd	\N	Odessa	TX	79762	US	(432) 367-0202	Robin Rutherford	The Art of Dentistry	4712 E. University Blvd	\N	Odessa	TX	79762	US	(432) 367-0202	fedex	556346	fedex_ground	FedEx Ground	\N
628	690895	2025-10-15	ligockidentalgroup@gmail.com	shipped	225102299	2	\N	X-Cart	2025-10-15 21:11:06.712059	2025-10-16 17:27:39.325556	\N	Mark Ligocki	Ligocki Dental Group	1S224 Summit Avenue\nSuite 104	\N	Oakbrook Terrace	IL	60181	US	6306208099	Mark Ligocki	Ligocki Dental Group	1S224 Summit Avenue\nSuite 104	\N	Oakbrook Terrace	IL	60181	US	6306208099	fedex	556346	fedex_ground	FedEx Ground	\N
630	690915	2025-10-15	drjordan@jordanfamilydentistry.net	shipped	225116498	3	\N	X-Cart	2025-10-15 21:11:06.712059	2025-10-16 17:27:39.325556	\N	Sherrill Jordan	Jordan Family Dentistry	12180 Highway 601 South	\N	Midland	NC	28107	US	(704) 781-0094	Sherrill Jordan	Jordan Family Dentistry	12180 Highway 601 South	\N	Midland	NC	28107	US	(704) 781-0094	fedex	556346	fedex_ground	FedEx Ground	\N
447	100525	2025-10-10	ravikumarr@pacden.com	cancelled	225067392	2	0	ShipStation Manual	2025-10-10 20:18:36	2025-10-15 17:58:04.892279	\N	Rakshith Arakotaram Ravikumar	BASTROP MODERN DENTISTRY	1670 HIGHWAY 71 E STE A	\N	BASTROP	TX	78602-2034	US	512-240-6496	Rakshith Arakotaram Ravikumar	BASTROP MODERN DENTISTRY	1670 HIGHWAY 71 E STE A	\N	BASTROP	TX	78602-2034	US	512-240-6496	fedex	556346	fedex_ground	FedEx Ground	\N
615	100529	2025-10-09	\N	shipped	225073050	0	\N	X-Cart	2025-10-15 17:16:51.60363	2025-10-15 17:58:04.892279	20251015_175428_141954	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
641	691025	2025-10-16	parkhillsdentistry@gmail.com	shipped	\N	1	\N	X-Cart	2025-10-16 13:50:30.586609	2025-10-16 17:27:39.325556	\N	Jinyoung Kim	Park Hills Dentistry	3122 Custer dr	\N	Lexington	KY	40517	US	(859) 967-3941	Jinyoung Kim	Park Hills Dentistry	3122 Custer dr	\N	Lexington	KY	40517	US	(859) 967-3941	fedex	556346	fedex_ground	FedEx Ground	\N
453	689545	2025-10-10	oscar.deleonvallejo@pacden.com	cancelled	224351398	7	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Oscar DeLeon	Bandera Modern Dentistry	9234 N Loop 1604 W\nste 121	\N	San Antonio	TX	78249	US	(210) 681-1121	Oscar DeLeon	Bandera Modern Dentistry	9234 N Loop 1604 W\nste 121	\N	San Antonio	TX	78249	US	(210) 681-1121	\N	\N	\N	\N	\N
456	689575	2025-10-13	denise_diaz_09@hotmail.com	shipped	224365077	1	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Denise Diaz	Family Smiles of Boerne	430 W Bandera Rd\nSte 4B	\N	Boerne	TX	78006	US	(830) 428-3698	Denise Diaz	Family Smiles of Boerne	430 W Bandera Rd\nSte 4B	\N	Boerne	TX	78006	US	(830) 428-3698	fedex	556346	fedex_ground	FedEx Ground	\N
616	100530	2025-10-10	\N	shipped	225073060	0	\N	X-Cart	2025-10-15 17:16:52.766853	2025-10-15 17:58:04.892279	20251015_175428_141954	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
465	689665	2025-10-13	info@fordingislanddental.com	shipped	224437383	3	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	\N	Nathan Buck	Fording Island Dental	201 Okatie Village Dr\nSuite 4	\N	Okatie	SC	29909	US	(843) 489-8463	Nathan Buck	Fording Island Dental	201 Okatie Village Dr\nSuite 4	\N	Okatie	SC	29909	US	(843) 489-8463	fedex	556346	fedex_ground	FedEx Ground	\N
467	689685	2025-10-13	info@peakcitydentistry.com	shipped	224450354	2	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	\N	Christopher Tikvart	Peak City Family Dentistry	200 W Chatham St	\N	Apex	NC	27502	US	9193628797	Christopher Tikvart	Peak City Family Dentistry	200 W Chatham St	\N	Apex	NC	27502	US	9193628797	fedex	556346	fedex_ground	FedEx Ground	\N
469	689715	2025-10-13	info@bryantstdental.com	shipped	224471034	1	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	\N	Chad Abed	Bryant St Dental	824 Bryant St	\N	Palo Alto	CA	94301	US	(650) 327-1787	Chad Abed	Bryant St Dental	824 Bryant St	\N	Palo Alto	CA	94301	US	(650) 327-1787	fedex	556346	fedex_ground	FedEx Ground	\N
470	689745	2025-10-13	pakdds@stonelake-familydentistry.com	shipped	224486172	6	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	\N	Martin Pak	Stonelake Family Dentistry PLLC	14550 SH 121,\nsuite 100	\N	Frisco	TX	75035	US	(214) 494-4246	Martin Pak	Stonelake Family Dentistry PLLC	14550 SH 121,\nsuite 100	\N	Frisco	TX	75035	US	(214) 494-4246	fedex	556346	fedex_ground	FedEx Ground	\N
471	689755	2025-10-13	elainegtdds@gmail.com	shipped	224502244	6	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	20251013_195003_650351	Elaine Gorelik	Trident Dentistry	11835 West Olympic Blvd\nste 400E - East Tower	\N	Los Angeles	CA	90064	US	3104441445	Elaine Gorelik	Trident Dentistry	450 N. Maple Drive\nApt 402	\N	Beverly Hills	CA	90210	US	310-444-1445	fedex	556346	fedex_ground	FedEx Ground	\N
472	689765	2025-10-13	dr.ian.klock@gmail.com	shipped	224502248	2	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	20251013_195003_650351	Ian Klock	Klockworks Chiropractic	4160 Washington Road\nBldg 2 ste 202	\N	McMurray	PA	15317	US	(724) 743-1050	Ian Klock	Klockworks Chiropractic	4160 Washington Road\nBldg 2 ste 202	\N	McMurray	PA	15317	US	(724) 743-1050	fedex	556346	fedex_ground	FedEx Ground	\N
474	689775	2025-10-13	popperdds@gmail.com	shipped	224504367	1	\N	X-Cart	2025-10-13 19:54:08	2025-10-16 17:27:39.325556	\N	John Popper	John R Popper, DDS	935 N Wilcox Drive	\N	Kingsport	TN	37660	US	(423) 246-6881	John Popper	John R Popper, DDS	935 N Wilcox Drive	\N	Kingsport	TN	37660	US	(423) 246-6881	fedex	556346	fedex_ground	FedEx Ground	\N
638	690975	2025-10-15	staff@thetoothery.com	shipped	\N	1	\N	X-Cart	2025-10-16 01:21:24.010066	2025-10-16 17:27:39.325556	20251016_012439_280894	Jessica Bertoglio	The Toothery	3049 Barrington Rd	\N	Hoffman Estates	IL	60192	US	(847) 893-9099	Jessica Bertoglio	The Toothery	3049 Barrington Rd	\N	Hoffman Estates	IL	60192	US	(847) 893-9099	fedex	556346	fedex_ground	FedEx Ground	\N
548	690205	2025-10-15	info@avantdentistryplano.com	shipped	224999418	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Karen Lee	Avant Dentistry	909 Legacy Drive #100	\N	Plano	TX	75023	US	(214) 699-9828	Karen Lee	Avant Dentistry	909 Legacy Drive #100	\N	Plano	TX	75023	US	(214) 699-9828	fedex	556346	fedex_ground	FedEx Ground	\N
556	690285	2025-10-15	drfarian@yahoo.com	shipped	225001908	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Olha Zhenchur	Zenon Farian DDS Inc.	229 E Wallings Road	\N	Broadview Heights	OH	44147	US	(440) 526-9100	Olha Zhenchur	Zenon Farian DDS Inc.	229 E Wallings Road	\N	Broadview Heights	OH	44147	US	(440) 526-9100	fedex	556346	fedex_ground	FedEx Ground	\N
565	690375	2025-10-15	purchasing@signaturedentalpartners.com	shipped	225001934	3	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Andrew T McCormick	Signature Dental Partners	855 Fountaingrove Pkwy.\nSuite 200	\N	Santa Rosa	CA	95403	US	707-579-9993	Darlene Langelier	Signature Dental Partners	410 North 44th St\nSte 600	\N	Phoenix	AZ	85008	US	(480) 626-5302	fedex	556346	fedex_ground	FedEx Ground	\N
617	100531	2025-10-10	\N	shipped	225073068	0	\N	X-Cart	2025-10-15 17:16:53.722101	2025-10-15 17:58:04.892279	20251015_175428_141954	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
631	690925	2025-10-15	drstepheniekaufmann@hotmail.com	shipped	225123499	6	\N	X-Cart	2025-10-15 21:11:06.712059	2025-10-16 17:27:39.325556	\N	stephenie kaufmann	Stephenie H Kaufmann DDS PC	po box 6069\n400W Midland Ave suite 110	\N	woodland park	CO	80866	US	(719) 687-4033	stephenie kaufmann	Stephenie H Kaufmann DDS PC	po box 6069\n400W Midland Ave suite 110	\N	woodland park	CO	80866	US	(719) 687-4033	fedex	556346	fedex_ground	FedEx Ground	\N
632	690935	2025-10-15	contact@bethesdadentalassociates.com	shipped	\N	2	\N	X-Cart	2025-10-15 21:11:06.712059	2025-10-16 17:27:39.325556	20251015_211145_608047	Nishu Singh-Afari	Bethesda Dental Associates	5413 W Cedar Ln\nSte 205C	\N	Bethesda	MD	20814	US	(301) 530-9111	Nishu Singh-Afari	Bethesda Dental Associates	5413 W Cedar Ln\nSte 205C	\N	Bethesda	MD	20814	US	(301) 530-9111	fedex	556346	fedex_ground	FedEx Ground	\N
635	690945	2025-10-15	anna@zenone.com	shipped	\N	6	\N	X-Cart	2025-10-15 21:45:04.53703	2025-10-16 17:27:39.325556	20251015_214844_303179	Ashkan Alizadeh	J Street Dental Group	2619 J Street	\N	Sacramento	CA	95816	US	(916) 759-0238	Ashkan Alizadeh	Sacramento River Dental Group	905 Secret River Dr.\nSte C	\N	Sacramento	CA	95661	US	9163914848	fedex	556346	fedex_ground	FedEx Ground	\N
111	684475	2025-09-17	info@inspiresmilessd.com	shipped	217595244	1	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Elona Gaball	INSPIRING SMILES	530 LOMAS SANTA FE DR STE A	\N	SOLANA BEACH	CA	92075-1346	US	(858) 876-9100	Elona Gaball	Inspiring Smiles	4735 Caminito Lapiz	\N	San Diego	CA	92130	US	8588769100	fedex	556346	fedex_ground	FedEx Ground	\N
636	690955	2025-10-15	shankdmd@gmail.com	shipped	\N	1	\N	X-Cart	2025-10-15 22:27:58.953486	2025-10-16 17:27:39.325556	20251015_222855_945135	Christopher Shank	Mountain View Dental Care	125 INVERNESS DR E STE 310	\N	ENGLEWOOD	CO	80112	US	(303) 960-3017	Christopher Shank	Mountain View Dental Care	125 INVERNESS DR E STE 310	\N	ENGLEWOOD	CO	80112	US	(303) 960-3017	fedex	556346	fedex_ground	FedEx Ground	\N
637	690965	2025-10-15	drcarlla@ptouchdental.com	shipped	\N	1	\N	X-Cart	2025-10-16 00:29:00.088846	2025-10-16 17:27:39.325556	20251016_002921_595593	Carlla Franklin	Pleasant Touch Dental	957 S. Mannheim Rd\nSuite 1-S	\N	Westchester	IL	60154	US	(708) 223-4360	Carlla Franklin	Pleasant Touch Dental	957 S. Mannheim Rd\nSuite 1-S	\N	Westchester	IL	60154	US	(708) 223-4360	fedex	556346	fedex_ground	FedEx Ground	\N
639	690995	2025-10-16	info@bridgesdental.com	shipped	225292241	1	\N	X-Cart	2025-10-16 13:24:07.299474	2025-10-16 17:27:39.325556	\N	Laura Bridges	Bridges Dental	4316 New River Hills Parkway	\N	Valrico	FL	33596	US	(813) 654-3399	Laura Bridges	Bridges Dental	4316 New River Hills Parkway	\N	Valrico	FL	33596	US	(813) 654-3399	fedex	556346	fedex_ground	FedEx Ground	\N
112	684645	2025-09-18	mda2@monroevilledental.com	shipped	217851121	1	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Sara Morman	MONROEVILLE DENTAL	136 RIDGE ST N STE C	\N	MONROEVILLE	OH	44847-9469	US	(419) 465-2574	Sara Morman	Monroeville Dental	136 Ridge Street N\nSuite C	\N	Monroeville	OH	44847	US	(419) 465-2574	fedex	556346	fedex_ground	FedEx Ground	\N
113	684655	2025-09-18	primedentalsmiles@gmail.com	shipped	217863961	1	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Guojun Ma	PRIME DENTAL CARE	77 TAMARACK CIR	\N	SKILLMAN	NJ	08558-2019	US	(609) 688-8818	Guojun Ma	Prime Dental Care	77 Tamarack Circle	\N	Montgomery	NJ	08558	US	(609) 688-8818	fedex	556346	fedex_ground	FedEx Ground	\N
114	684665	2025-09-18	drdellabella@drdellabella.com	shipped	217866738	2	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Alex M. Della Bella Alex M. Della Bella	CINCINNATI DENTAL EXCELLENCE	7835 REMINGTON RD	\N	MONTGOMERY	OH	45242-7155	US	(513) 793-1977	Alex M. Della Bella Alex M. Della Bella	Cincinnati Dental Excellence	7835 Remington Road	\N	Cincinnati	OH	45242	US	(513) 793-1977	fedex	556346	fedex_ground	FedEx Ground	\N
115	684675	2025-09-18	jessemgoldman@gmail1.com	shipped	217873301	2	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Jesse Goldman	GENESEE DENTAL GROUP	25918 GENESEE TRAIL RD STE 210	\N	GOLDEN	CO	80401-5775	US	(303) 526-9155	Jesse Goldman	Billing	454 Entrada Drive	\N	Golden	CO	80401	US	978-886-5866	fedex	556346	fedex_ground	FedEx Ground	\N
116	684685	2025-09-18	truongpongdds@gmail.com	shipped	217874490	2	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Melody Pongmanopap	ADVANCED DENTISTRY OF WOODLAND	255 W COURT ST STE C	\N	WOODLAND	CA	95695-2986	US	(530) 666-2117	Melody Pongmanopap	Advanced Dentistry of Woodland	255 W Court St \nSuite C	\N	Woodland	CA	95695	US	(530) 666-2117	fedex	556346	fedex_ground	FedEx Ground	\N
117	684695	2025-09-18	frontdesk@tryondental.com	shipped	218063015	2	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Derrell Hood	TRYON FAMILY DENTISTRY	70 DEPOT ST	\N	TRYON	NC	28782-3358	US	(828) 859-5839	Derrell Hood	TRYON FAMILY DENTISTRY	70 DEPOT ST	\N	TRYON	NC	28782-3358	US	8288595830	fedex	556346	fedex_ground	FedEx Ground	\N
118	684715	2025-09-18	BruceSeaderDDS@gmail.com	shipped	217885172	1	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Bruce Seader	BRUCE SEADERDDS	1 ELM ST STE 1A	\N	TUCKAHOE	NY	10707-3939	US	(914) 793-9080	Bruce Seader	Bruce SeaderDDS	1 Elm Street\n1-A	\N	Tuckahoe	NY	10707	US	(914) 793-9080	fedex	556346	fedex_ground	FedEx Ground	\N
119	684725	2025-09-18	gloriaalvarezdds@gmail.com	shipped	217907397	6	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Gloria Alvarez-Kiely	ROSWELL DENTAL STUDIO	355 S ATLANTA ST	\N	ROSWELL	GA	30075-4934	US	(770) 998-1466	Gloria Alvarez-Kiely	Roswell Dental Studio	355 S. Atlanta street	\N	Roswell	GA	30075	US	(770) 998-1466	fedex	556346	fedex_ground	FedEx Ground	\N
120	684735	2025-09-18	toothdds@gmail.com	shipped	218062885	6	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-03 17:42:12	\N	Danny Shiri	DANNY SHIRI	6310 SAN VICENTE BLVD STE 295	\N	LOS ANGELES	CA	90048-5454	US	(310) 770-8912	Danny Shiri	danny shiri	6310 San Vicente Blvd Ste 295	\N	Los Angeles	CA	90048	US	(310) 770-8912	fedex	556346	fedex_ground	FedEx Ground	\N
121	684755	2025-09-19	office@bperio.com	shipped	218079422	6	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Thomas Bodnar	BODNAR PERIODONTICS	21851 CENTER RIDGE RD STE 104	\N	ROCKY RIVER	OH	44116-3901	US	(440) 331-3044	Thomas Bodnar	Bodnar Periodontics	4354 Valley Forge Drive	\N	Fairview Park	OH	44126	US	4403313044	fedex	556346	fedex_ground	FedEx Ground	\N
122	684765	2025-09-19	smile@dentalhaven.com	shipped	218108932	6	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Grace Maniego	DENTAL HAVEN	508 GIBSON DR STE 100 STE 100	\N	ROSEVILLE	CA	95678-5795	US	(916) 772-6777	Grace Maniego	Dental Haven	508 Gibson Drive STE 100\nSTE 100	\N	Roseville	CA	95678	US	(916) 772-6777	fedex	556346	fedex_ground	FedEx Ground	\N
123	684775	2025-09-19	calebhodgesdmd@gmail.com	shipped	218133761	6	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Caleb Hodges	HODGES FAMILY DENTAL	102 S MALONE ST STE D	\N	ATHENS	AL	35611-2476	US	(256) 232-4212	Caleb Hodges	Hodges Family Dental	102 S MALONE ST\nSuite D	\N	ATHENS	AL	35611	US	(256) 232-4212	fedex	556346	fedex_ground	FedEx Ground	\N
124	684785	2025-09-19	stephensstaff@yahoo.com	shipped	218133763	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Brian Stephens	STEPHENS FAMILY DENTISTRY	1525 N WASHINGTON ST	\N	WEATHERFORD	OK	73096-2518	US	(580) 772-2711	Brian Stephens	Stephens Family Dentistry	1525 N Washington St	\N	Weatherford	OK	73096	US	(580) 772-2711	fedex	556346	fedex_ground	FedEx Ground	\N
125	684795	2025-09-19	info@snc.dental	shipped	218160234	2	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Brianna Stoterau	S&C DENTAL	17767 N SCOTTSDALE RD STE 110	\N	SCOTTSDALE	AZ	85255-6590	US	(480) 691-0020	Brianna Stoterau	S&C Dental	17767 N SCOTTSDALE RD STE 110	\N	SCOTTSDALE	AZ	85255	US	(480) 691-0020	fedex	556346	fedex_ground	FedEx Ground	\N
126	684805	2025-09-19	dentalassistant@dentonsmilesdentistry.com	shipped	218211025	6	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Susan  Tran	DENTON SMILES DENTISTRY	721 S INTERSTATE 35 E STE 206	\N	DENTON	TX	76205-8153	US	(940) 380-1188	Susan  Tran	Denton Smiles Dentistry	721 S Interstate 35\nste 206	\N	Denton	TX	76205	US	(940) 380-1188	fedex	556346	fedex_ground	FedEx Ground	\N
127	684815	2025-09-20	kgkordsmeier@gmail.com	shipped	218676702	5	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Keith G Kordsmeier	DENTISTRY REVOLUTION	1591 YANCEYVILLE ST STE 200B	\N	GREENSBORO	NC	27405-6943	US	+3366873572	Keith Kordsmeier	Dentistry Revolution	1591 Yanceyville St.\nSTE 200 B	\N	Greensboro	NC	27405	US	(336) 272-6235	fedex	556346	fedex_ground	FedEx Ground	\N
128	684825	2025-09-20	tyjoncas@hotmail.com	shipped	218676704	6	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	George Joncas	JONCAS FAMILY DENTISTRY PC	5840 MACARTHUR BLVD NW	\N	WASHINGTON	DC	20016-2542	US	(202) 363-5840	George Joncas	Billing	10139 Crestwood Road	\N	Kensington	NJ	20895	US	2023635840	fedex	556346	fedex_ground	FedEx Ground	\N
129	684835	2025-09-20	drsaab@houstondentistry.com	shipped	218676705	2	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Dealla Saab	HOUSTON DENTISTRY AT MEMORIAL	2450 FONDREN RD STE 250	\N	HOUSTON	TX	77063-2326	US	(713) 789-4300	Dealla Saab	Houston Dentistry at Memorial	2450 Fondren Rd\n250	\N	Houston	TX	77063	US	(713) 789-4300	fedex	556346	fedex_ground	FedEx Ground	\N
130	684855	2025-09-22	kdoker18@gmail.com	shipped	218718937	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Kricket Doker	GUFFEE DENTAL ASSOCIATES	26 HOLLY CREEK DR	\N	ANDERSON	SC	29621-2195	US	(864) 226-1752	Kricket Doker	Guffee Dental Associates	26 Holly Creek Drive	\N	Anderson	SC	29621	US	(864) 226-1752	fedex	556346	fedex_ground	FedEx Ground	\N
131	684865	2025-09-22	Sneedentalassociates@yahoo.com	shipped	218718940	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Ryan Snee	SNEE DENTAL	1145 E MAIDEN ST	\N	WASHINGTON	PA	15301-3737	US	(724) 222-0380	Ryan Snee	Snee Dental	1145 E Maiden St	\N	Washington	PA	15301	US	(724) 222-0380	fedex	556346	fedex_ground	FedEx Ground	\N
132	684875	2025-09-22	jswinson@dentistsofalbuquerque.com	shipped	218725750	6	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Davis Gribble	DAVIS GRIBBLE HOLLOWWA DENTAL	3610 CALLE CUERVO NW	\N	ALBUQUERQUE	NM	87114-8904	US	(505) 898-1976	Davis Gribble	Davis Gribble Hollowwa Dental	3610 Calle Cuervo NW	\N	Albuquerque	NM	87114	US	(505) 898-1976	fedex	556346	fedex_ground	FedEx Ground	\N
133	684885	2025-09-22	houmafamilydental219@gmail.com	shipped	218732601	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Stephen Morgan	HOUMA, LA	5683 HIGHWAY 311	\N	HOUMA	LA	70360-5595	US	(985) 868-5699	Stephen Morgan	HOUMA, LA	5683 Highway 311	\N	HOUMA, LA	LA	70360	US	(985) 868-5699	fedex	556346	fedex_ground	FedEx Ground	\N
134	684905	2025-09-22	applewooddentalwr@gmail.com	shipped	218749022	2	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Erin Cettie	APPLEWOOD DENTAL	12495 W 32ND AVE STE 2	\N	WHEAT RIDGE	CO	80033-5290	US	(303) 237-2707	Erin Cettie	Applewood dental	12495 W 32nd Ave\nSuite 2	\N	Wheat Ridge	CO	80033	US	(303) 237-2707	fedex	556346	fedex_ground	FedEx Ground	\N
135	684915	2025-09-22	whitedental91@gmail.com	shipped	218749025	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Jake Madsen	WHITE DENTAL	431 W 600 N	\N	TREMONTON	UT	84337-2411	US	(435) 257-3210	Jake Madsen	White Dental	431 W 600 N	\N	Tremonton	UT	84337	US	(435) 257-3210	fedex	556346	fedex_ground	FedEx Ground	\N
136	684925	2025-09-22	info@atowndental.com	shipped	218789298	2	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Nathan Brooks	ANDERSON DENTAL CARE	7525 STATE RD STE A	\N	CINCINNATI	OH	45255-6406	US	(513) 231-7755	Nathan Brooks	ANDERSON DENTAL CARE	7525 STATE RD STE A	\N	CINCINNATI	OH	45255-6406	US	(513) 231-7755	fedex	556346	fedex_ground	FedEx Ground	\N
137	684935	2025-09-22	info@outstandingsmile.com	shipped	218770311	15	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Cameron Perigo	ESTHETIC FAMILY DENTISTRY, LLC	8580 SCARBOROUGH DR STE 105	\N	COLORADO SPGS	CO	80920-7583	US	719-528-5577	Cameron Perigo	Esthetic Family Dentistry, LLC	8580 Scarborough\nSuite 105	\N	Colorado Springs	CO	80920	US	719-528-5577	fedex	556346	fedex_ground	FedEx Ground	\N
138	684945	2025-09-22	srdental@att.net	shipped	218789371	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Chelsey Daily	STERLING RIDGE DENTAL	6700 WOODLANDS PKWY STE 160	\N	THE WOODLANDS	TX	77382-2577	US	2813633308	Chelsey Daily	STERLING RIDGE DENTAL	6700 WOODLANDS PKWY STE 160	\N	THE WOODLANDS	TX	77382-2577	US	2813633308	fedex	556346	fedex_ground	FedEx Ground	\N
139	684955	2025-09-22	samaracwdc@yahoo.com	shipped	218790180	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Young An	CALIFORNIA WAVE DENTAL CENTER INC	15436 DEVONSHIRE ST	\N	MISSION HILLS	CA	91345-2619	US	(818) 988-9959	Young An	california wave dental center inc	15436 Devonshire St	\N	Mission Hills	CA	91345	US	(818) 988-9959	fedex	556346	fedex_ground	FedEx Ground	\N
140	684965	2025-09-22	manager@kannapolisfamilydentistry.com	shipped	218792173	15	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Matt Rivera	KANNAPOLIS FAMILY DENTISTRY	814 SLOOP AVE	\N	KANNAPOLIS	NC	28083-2992	US	(704) 933-2116	Matt Rivera	Kannapolis Family Dentistry	814 Sloop Ave	\N	Kannapolis	NC	28083	US	(704) 933-2116	fedex	556346	fedex_ground	FedEx Ground	\N
141	684975	2025-09-22	shchass@aol.com	shipped	218804829	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Sharon Chass	SHARON A CHASS DMD	115 E 61ST ST FL 8	\N	NEW YORK	NY	10065-8183	US	2126449340	Sharon Chass	Sharon A Chass DMD	115 East 61st Street\n8th floor	\N	New York	NY	10065	US	2126449340	fedex	556346	fedex_ground	FedEx Ground	\N
340	688515	2025-10-06	mojganhashemi@rocketmail.com	shipped	222516200	6	\N	X-Cart	2025-10-06 18:29:48	2025-10-15 21:13:44.144495	\N	Mojgan Hashemi	Los Robles	415 Rolling Oaks Drive \nSuite 120	\N	Thousand Oak	CA	91361	US	(310) 367-6161	Mojgan Hashemi	Los Robles	415 Rolling Oaks Drive \nSuite 120	\N	Thousand Oak	CA	91361	US	(310) 367-6161	fedex	556346	fedex_2day	FedEx 2Day	\N
143	684995	2025-09-22	drorlosky@gmail.com	shipped	218818058	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Ryan  Orlosky	LEFBERG DENTAL	2 TOWN SQUARE BLVD STE 210	\N	ASHEVILLE	NC	28803-5032	US	(828) 684-3305	Ryan  Orlosky	Lefberg Dental	2 Town Square Blvd. \nSuite 210	\N	Asheville	NC	28803	US	(828) 684-3305	fedex	556346	fedex_ground	FedEx Ground	\N
144	685005	2025-09-22	admin@hittsondental.com	shipped	218820278	6	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-03 17:42:12	\N	Suzanne Hittson	HITTSON DENTAL	3301 N GOLIAD ST STE 107	\N	ROCKWALL	TX	75087-7193	US	(972) 771-3753	Suzanne Hittson	Hittson Dental	3301 N. Goliad St.\nSte. 107	\N	Rockwall	TX	75087	US	(972) 771-3753	fedex	556346	fedex_ground	FedEx Ground	\N
145	685015	2025-09-22	cpdorders@ccfdmail.com	shipped	218827856	2	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Cecilia Liu	COASTAL PEDIATRIC DENTISTRY	3067 SOUTHPORT SUPPLY RD SE	\N	BOLIVIA	NC	28422-7943	US	(910) 253-0006	Cecilia Liu	Coastal Pediatric Dentistry	3067 South Port Supply Road SE	\N	Bolivia	NC	28422	US	(910) 253-0006	fedex	556346	fedex_ground	FedEx Ground	\N
146	685025	2025-09-22	team@christinekirchnerdds.com	shipped	218835497	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Christine Kirchner	CHRISTINE KIRCHNER, D.D.S. G & C D	6451 FAUNTLEROY WAY SW	\N	SEATTLE	WA	98136-1881	US	(206) 938-4540	Christine Kirchner	Christine Kirchner, D.D.S. General & Cosmetic Dentistry	6451 FAUNTLEROY WAY SW	\N	SEATTLE	WA	98136	US	(206) 938-4540	fedex	556346	fedex_ground	FedEx Ground	\N
147	685035	2025-09-22	info@beechnutdentalcare.com	shipped	218838549	2	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Kevin Freeman	BEECHNUT DENTAL CARE	4660 BEECHNUT ST STE 228	\N	HOUSTON	TX	77096-1817	US	(713) 839-0900	Kevin Freeman	Beechnut Dental Care	4660 Beechnut\nste 228	\N	Houston	TX	77096	US	(713) 839-0900	fedex	556346	fedex_ground	FedEx Ground	\N
148	685045	2025-09-22	info@lifesmilesofnewhope.com	shipped	219071423	2	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Dharmesh Parbhoo	LIFE SMILES OF NEW HOPE	49 HOSIERY MILL RD STE 125	\N	DALLAS	GA	30157-1688	US	(770) 445-1314	Dharmesh Parbhoo	LIFE SMILES OF NEW HOPE	49 HOSIERY MILL RD STE 125	\N	DALLAS	GA	30157-1688	US	(770) 445-1314	fedex	556346	fedex_ground	FedEx Ground	\N
149	685055	2025-09-22	nate@prepphys.com	shipped	218844881	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Melanie Bagley	PREPARED PHYSICIAN	75 W 100 S STE 140	\N	LOGAN	UT	84321-5840	US	435 -250-4363	Nathan Whittaker	Prepared Physician	3414 N 1800 E	\N	North Logan	UT	84341	US	(435) 881-4335	fedex	556346	fedex_ground	FedEx Ground	\N
150	100493	2025-09-22	newbraunfels2bf@pacden.com	shipped	218730543	6	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-07 05:21:01	\N	Robert Kantz	NEW BRAUNFELS MODERN DENTISTRY	244 FM 306 STE 118	\N	NEW BRAUNFELS	TX	78130-5487	US	830-201-1223	Robert Kantz	\N	\N	\N	\N	\N	\N		830-201-1223	fedex	556346	fedex_ground	FedEx Ground	\N
151	685065	2025-09-22	edivito@azcld.com	shipped	218851397	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Enrico DiVito	ARIZONA CENTER FOR LASER DENTISTRY	7900 E THOMPSON PEAK PKWY STE 101	\N	SCOTTSDALE	AZ	85255-7400	US	(480) 990-1905	Enrico DiVito	Arizona Center for Laser Dentistry	7900 E. Thompson Peak Parkway \n#101	\N	Scottsdale	AZ	85255	US	(480) 990-1905	fedex	556346	fedex_ground	FedEx Ground	\N
152	685075	2025-09-22	info@belreddental.com	shipped	218866101	6	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Su Young Choi	BEL-RED DENTAL	15446 BEL RED RD STE 110	\N	REDMOND	WA	98052-5507	US	(425) 883-3656	Su Young Choi	Bel-Red Dental	15446 Bel-Red Road\nSuite 110	\N	Redmond	WA	98052	US	(425) 883-3656	fedex	556346	fedex_ground	FedEx Ground	\N
153	685085	2025-09-22	supplies@saperioimplant.com	shipped	218997195	2	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Steven Maller	DR. STEVEN C. MALLER, DDS, MS, PC	4501 MCCULLOUGH AVE STE 104	\N	SAN ANTONIO	TX	78212-1659	US	(210) 824-0111	Steven Maller	Dr. Steven C. Maller, DDS, MS, PC	4501 McCullough Ave\nste 104	\N	San Antonio	TX	78212	US	(210) 824-0111	fedex	556346	fedex_ground	FedEx Ground	\N
154	685095	2025-09-22	VICTORIASM@GMAIL.COM	shipped	218997196	2	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	VICTORIA MOSUR	VICTORIA S MOSUR DDS	898 5TH ST STE A	\N	LINCOLN	CA	95648-1774	US	9166453373	VICTORIA MOSUR	VICTORIA S MOSUR DDS	898 5th St, Ste A	\N	Lincoln	CA	95648	US	9166453373	fedex	556346	fedex_ground	FedEx Ground	\N
155	685105	2025-09-22	riverwestdental@gmail.com	shipped	218997197	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Chandler Bell	RIVERWEST DENTAL	1655 PANCHERI DR	\N	IDAHO FALLS	ID	83402-3169	US	(208) 522-1911	Chandler Bell	RiverWest Dental	1655 Pancheri Dr.	\N	Idaho Falls	ID	83402	US	(208) 522-1911	fedex	556346	fedex_ground	FedEx Ground	\N
156	685125	2025-09-22	fcsmilesdrp@gmail.com	shipped	219002259	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Niral Patel	FOUNTAIN CITY SMILES	2944 TAZEWELL PIKE STE 2	\N	KNOXVILLE	TN	37918-1990	US	(860) 938-1745	Niral Patel	Fountain City Smiles	2944 Tazewell Pike\nSuite 2	\N	Knoxville	TN	37918	US	(860) 938-1745	fedex	556346	fedex_ground	FedEx Ground	\N
157	685135	2025-09-23	rachel1.positive@gmail.com	shipped	219004175	15	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Christopher Allington	POSITIVE IMAGE DENTAL/ BWS-BOSS LTD.	825 FRELINGHUYSEN AVE	\N	NEWARK	NJ	07114-2216	US	973-242-3315	Christopher Allington	Positive Image Dental	PO BOX 143 Hyde Park	\N	Vermont	NH	05655	US	8028883727	fedex	556346	fedex_ground	FedEx Ground	\N
158	685145	2025-09-23	brittany@centralmainesmiles.com	shipped	219008542	2	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Brittany Cunningham	CENTRAL MAINE SMILES	5 WINTER ST	\N	DOVR FOXCROFT	ME	04426-1022	US	(207) 564-3455	Brittany Cunningham	Central Maine Smiles	5 Winter St	\N	Dover-Foxcroft	ME	04426	US	(207) 564-3455	fedex	556346	fedex_ground	FedEx Ground	\N
159	685155	2025-09-23	dr.ian.klock@gmail.com	shipped	219014222	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Ian Klock	KLOCKWORKS CHIROPRACTIC	4160 WASHINGTON RD STE 202 BLDG 2	\N	MCMURRAY	PA	15317-2533	US	(724) 743-1050	Ian Klock	Klockworks Chiropractic	4160 Washington Road\nBldg 2 ste 202	\N	McMurray	PA	15317	US	(724) 743-1050	fedex	556346	fedex_ground	FedEx Ground	\N
160	685165	2025-09-23	candy@nextdentistry.com	shipped	219021674	15	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Veronika Vazquez	NEXT DENTISTRY	110 HARDEN PKWY STE 102	\N	SALINAS	CA	93906-5257	US	(831) 449-4567	Veronika Vazquez	Next Dentistry	4360 Slide MTN circle	\N	Reno	CA	89511	US	831-596-2473	fedex	556346	fedex_ground	FedEx Ground	\N
161	685185	2025-09-23	gp@gpdentalgroup.com	shipped	219022608	3	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Dory Sellers	GROVE PARK DENTAL GROUP	4515 POPLAR AVE STE 406	\N	MEMPHIS	TN	38117-7508	US	(901) 683-9800	Dory Sellers	Grove Park Dental Group	4515 Poplar Ave\nSte 406	\N	Memphis	TN	38117	US	(901) 683-9800	fedex	556346	fedex_ground	FedEx Ground	\N
162	685195	2025-09-23	Angiehopper@premdent.com	shipped	219022614	6	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Pamela Gowan	PREMIER DENTAL CENTER	14029 S 1ST ST	\N	MILAN	TN	38358-6195	US	(731) 613-2800	Chris Arnold	Premier Dental Center	7019 Hwy 412 South	\N	Bells	TN	38006	US	7316639999	fedex	556346	fedex_ground	FedEx Ground	\N
163	685205	2025-09-23	info@8118dental.com	shipped	219024112	4	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Tana Busch	8118 DENTAL PROFESSIONALS	8118 SHOAL CREEK BLVD	\N	AUSTIN	TX	78757-8041	US	(512) 452-8262	Tana Busch	8118 Dental Professionals	8118 Shoal Creek Blvd.	\N	Austin	TX	78757	US	(512) 452-8262	fedex	556346	fedex_ground	FedEx Ground	\N
164	685215	2025-09-23	Scotjaclyn@yahoo.com	shipped	219071346	3	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Jaclyn N. Smith, DDS, PC	THE DENTIST, PLLC	301 HIGHWAY 71 W STE 200	\N	BASTROP	TX	78602-4111	US	(512) 303-4545	Jaclyn N. Smith, DDS, PC	THE DENTIST, PLLC	301 HIGHWAY 71 W STE 200	\N	BASTROP	TX	78602-4111	US	(512) 303-4545	fedex	556346	fedex_ground	FedEx Ground	\N
165	685225	2025-09-23	petershumakerdds@yahoo.com	shipped	219034335	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Mary Ann Shumaker	PETER E. SHUMAKER, DDS, MS	17220 MACK AVE STE 3	\N	GROSSE POINTE	MI	48230-6254	US	(313) 886-3120	Mary Ann Shumaker	Peter E. Shumaker, DDS, MS	17220 Mack Ave	\N	Grosse Pointe	MI	48230	US	(313) 886-3120	fedex	556346	fedex_ground	FedEx Ground	\N
166	685255	2025-09-23	maxrodefferdmd@gmail.com	shipped	219041820	2	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Max Rodeffer	MAX A. RODEFFER, DMD	911 BROADWAY ST	\N	HAMILTON	IL	62341-1436	US	(217) 847-3900	Max Rodeffer	Max A. Rodeffer, DMD	911 Broadway Street	\N	Hamilton	IL	62341	US	(217) 847-3900	fedex	556346	fedex_ground	FedEx Ground	\N
167	685265	2025-09-23	info@gasmileteam.com	shipped	219042936	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Matt Dunford	GEORGIA SMILE TEAM	578 S ENOTA DR NE	\N	GAINESVILLE	GA	30501-8947	US	(770) 536-3254	Matt Dunford	Georgia Smile Team	578 South Enota Drive NE\nSte B	\N	Gainesville	GA	30501	US	(770) 536-3254	fedex	556346	fedex_ground	FedEx Ground	\N
168	685275	2025-09-23	office.kennyroadfamilydental@gmail.com	shipped	219045843	15	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Bradley  McCormack	MCCORMACK DENTAL GROUP	4589 KENNY RD	\N	COLUMBUS	OH	43220-2770	US	(614) 451-2727	Bradley  McCormack	McCormack Dental Group	4589 Kenny Rd	\N	Columbus	OH	43220	US	(614) 451-2727	fedex	556346	fedex_ground	FedEx Ground	\N
169	685285	2025-09-23	lawhondental@gmail.com	shipped	219051046	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Tanya Lawhon	DR. TANYA PIERCE LAWHON, DDS	116 S 4TH ST	\N	KINGSVILLE	TX	78363-5411	US	(361) 595-4121	Tanya Lawhon	Dr. Tanya Pierce Lawhon, DDS	116 South 4th Street	\N	Kingsville	TX	78363	US	(361) 595-4121	fedex	556346	fedex_ground	FedEx Ground	\N
170	685295	2025-09-23	info@pidsa.net	shipped	219071397	2	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	David A. Little	PROFESSIONALS IN DENTISTRY	6961 US HIGHWAY 87 E	\N	SAN ANTONIO	TX	78263-6029	US	(210) 648-4411	Dawn Meseke	PROFESSIONALS IN DENTISTRY	6961 US HIGHWAY 87 E	\N	SAN ANTONIO	TX	78263-6029	US	(210) 648-4411	fedex	556346	fedex_ground	FedEx Ground	\N
171	685305	2025-09-23	jlee@eaglevalleydental.com	shipped	219051054	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Jerry Lee	EAGLE VALLEY DENTAL	683 BIELENBERG DR STE 205	\N	WOODBURY	MN	55125-1715	US	(651) 200-4747	Jerry Lee	Eagle Valley Dental	683 Bielenberg Dr.\nsuite 205	\N	woodbury	MN	55125	US	(651) 200-4747	fedex	556346	fedex_ground	FedEx Ground	\N
172	685315	2025-09-23	mail@diazprosthodontics.com	shipped	219085639	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Joel Diaz	DIAZ PROSTHODONTICS	8706 FREDERICKSBURG RD STE 105	\N	SAN ANTONIO	TX	78240-1293	US	(210) 774-4241	Joel Diaz	Diaz Prosthodontics	8706 Fredericksburg Rd Suite 105	\N	San Antonio	TX	78240	US	(210) 774-4241	fedex	556346	fedex_ground	FedEx Ground	\N
173	100494	2025-09-23		shipped	219003914	6	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-07 05:21:01	\N	Westpointe Modern Dentistry 728	WESTPOINTE MODERN DENTISTRY 728	1659 STATE HWY 46 W STE 180	\N	NEW BRAUNFELS	TX	78132-4746	US	\N	Westpointe Modern Dentistry 728	\N	\N	\N	\N	\N	\N		\N	fedex	556346	fedex_ground	FedEx Ground	\N
174	685325	2025-09-23	Bscottederdds@gmail.com	shipped	219107633	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	B. Scott Eder	B. SCOTT EDER DDS	71 MACCORKLE AVE SW	\N	S CHARLESTON	WV	25303-1411	US	(304) 744-8448	B. Scott Eder	B. Scott Eder DDS	71 MacCorkle Ave SW	\N	South Charleston	WV	25303	US	(304) 744-8448	fedex	556346	fedex_ground	FedEx Ground	\N
175	685335	2025-09-23	office@longhollowdental.com	shipped	219100789	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Stephanie  Harding	LONG HOLLOW DENTAL	3100 BUSINESS PARK CIR STE 100	\N	GOODLETTSVLLE	TN	37072-2366	US	(615) 851-7102	Stephanie  Harding	Long Hollow Dental	3100 Business Park Circle \nSte 100	\N	Goodlettsville	TN	37072	US	(615) 851-7102	fedex	556346	fedex_ground	FedEx Ground	\N
176	685345	2025-09-23	Naghy@yahoo.com	shipped	219102281	6	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Naghmeh Yadegar	NEW AGE DENTAL	14545 TELEGRAPH RD	\N	LA MIRADA	CA	90638-1054	US	(562) 777-1188	Naghmeh Yadegar	New age dental	1250 s beverly glen blvd\nApt 312	\N	Los angeles	CA	90024	US	3102105162	fedex	556346	fedex_ground	FedEx Ground	\N
177	685355	2025-09-23	m.k.davis2010@gmail.com	shipped	219105906	6	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Michelle Davis	MICHELLE DAVIS DENTAL	7800 PARKWAY DR	\N	LEEDS	AL	35094-2119	US	(205) 699-8583	Michelle Davis	Michelle Davis Dental	7800 Parkway Dr	\N	Leeds	AL	35094	US	(205) 699-8583	fedex	556346	fedex_ground	FedEx Ground	\N
178	685365	2025-09-23	bartolomei@jbartolomeidds.com	shipped	219109288	1	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Jose Bartolomei	JOSE L. BARTOLOMEI, D.D.S.	4000 W HOWARD AVE	\N	GREENFIELD	WI	53221-1045	US	(414) 431-1595	Jose Bartolomei	Jose L. Bartolomei, D.D.S.	4000 West Howard Avenue	\N	Greenfield	WI	53221	US	(414) 431-1595	fedex	556346	fedex_ground	FedEx Ground	\N
179	685375	2025-09-23	luckhardtpllc@gmail.com	shipped	219109292	15	0	ShipStation Manual	2025-10-02 21:38:27	2025-10-03 17:42:12	\N	Diana Millard	COMPLETE DENTISTRY	10801 WOODLAND BEAVER RD STE 101	\N	CHARLOTTE	NC	28215-5177	US	(704) 888-0607	Diana Millard	Complete Dentistry	12925 Highway 601 South\nSuite 200	\N	Midland	NC	28107	US	7048880607	fedex	556346	fedex_ground	FedEx Ground	\N
180	685385	2025-09-23	administrator@encoredentalcv.com	shipped	219112992	6	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Anne Mary Pham	CREATIVE DIMENSIONS IN DENTISTRY- CASTRO VALLEY	20265 LAKE CHABOT RD	\N	CASTRO VALLEY	CA	94546-5307	US	(510) 881-8130	Kevin Cabugao	Creative Dimensions in Dentistry	11 Duffy Court	\N	Pleasant Hill	CA	94523	US	5108818010	fedex	556346	fedex_ground	FedEx Ground	\N
181	685395	2025-09-23	george.epperson50@gmail.com	shipped	219122405	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	George Epperson	GEORGE EPPERSON DDS	801 CRESCENT WAY STE 1	\N	ARCATA	CA	95521-6781	US	(707) 822-1785	George Epperson	George Epperson, DDS	175 Green Road	\N	Kneeland	CA	95549	US	(707) 822-1785	fedex	556346	fedex_ground	FedEx Ground	\N
182	685405	2025-09-23	officemgr@carewelldental.com	shipped	219122407	6	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Resmi Nair	CAREWELL DENTAL P.C.	102 MAIN ST	\N	RUTLAND	MA	01543-1309	US	508-886-6046	Resmi Nair	Carewell Dental	4 Laurel Ridge Lane	\N	Shrewsbury	MA	01545	US	5088866046	fedex	556346	fedex_ground	FedEx Ground	\N
183	685415	2025-09-23	drbradynj@gmail.com	shipped	219132014	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Kelli Brady	KELLY BRADY DDS LLC	510 BROADWAY	\N	NORWOOD	NJ	07648-1304	US	2017685553	Kelli Brady	Kelly Brady DDS LLC	510 Broadway	\N	Norwood	NJ	07648	US	2017685553	fedex	556346	fedex_ground	FedEx Ground	\N
184	685445	2025-09-23	ccr3@reagan.com	shipped	219135417	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	C C Rice	COMPLETE DENTAL CARE	2107 CONRAD HILTON BLVD	\N	CISCO	TX	76437-5129	US	(325) 518-6321	C C Rice Rice	Billing	101 South Hillcrest Ave	\N	Eastland	TX	76448	US	3255186321	fedex	556346	fedex_ground	FedEx Ground	\N
185	685455	2025-09-23	grenadadental1@yahoo.com	shipped	219139214	2	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Olivia Van Gordan	GRENADA DENTAL CLINIC	1800 F S HILL DR STE A	\N	GRENADA	MS	38901-5071	US	(662) 226-1757	Olivia Van Gordan	Grenada Dental Clinic	1800 F S Hill Drive\n Suite A	\N	Grenada	MS	38901	US	(662) 226-1757	fedex	556346	fedex_ground	FedEx Ground	\N
186	685465	2025-09-23	adamsbyrnesdentistry@gmail.com	shipped	219145003	6	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Briana Byrnes	BRIANA BYRNES	765 PAWLING AVE	\N	TROY	NY	12180-6214	US	(518) 283-6285	Briana Byrnes	Briana Byrnes	765 Pawling Ave.	\N	TROY	NY	12180	US	(518) 283-6285	fedex	556346	fedex_ground	FedEx Ground	\N
187	100495	2025-09-23		shipped	219033504	8	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-07 05:21:01	\N	Michael Bonner	HOME	3407 TREE HILL ST	\N	SAN ANTONIO	TX	78230-2435	US	\N	Michael Bonner	\N	\N	\N	\N	\N	\N		\N	fedex	556346	fedex_home_delivery	FedEx Home Delivery	\N
188	685475	2025-09-23	Hello@appleblossomdental.com	shipped	219260751	6	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Eric Whiting	APPLE BLOSSOM DENTAL	2618 W 7800 S STE 100	\N	WEST JORDAN	UT	84088-4212	US	(801) 566-1031	Eric Whiting	Apple Blossom Dental	2618 W 7800 S\n#100	\N	West Jordan	UT	84088	US	(801) 566-1031	fedex	556346	fedex_ground	FedEx Ground	\N
189	685485	2025-09-23	clinedentaloffice@gmail.com	shipped	219260754	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Brent Cline	CLINE FAMILY & COSMETIC DENTISTRY	3365 S HOLMES AVE	\N	IDAHO FALLS	ID	83404-7981	US	(208) 529-0420	Brent Cline	Cline Family & Cosmetic Dentistry	3365 S. Holmes Ave.	\N	Idaho Falls	ID	83404	US	(208) 529-0420	fedex	556346	fedex_ground	FedEx Ground	\N
190	685495	2025-09-23	info@townelakedentistry.com	shipped	219260760	6	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Trey Patterson	TOWNE LAKE DENTISTRY	9740 BARKER CYPRESS RD STE 113	\N	CYPRESS	TX	77433-1975	US	(832) 220-4300	BLLING BILLING	billing	13139 Tarbet Place Court	\N	Cypress	TX	77429	US	281-536-1004	fedex	556346	fedex_ground	FedEx Ground	\N
191	100497	2025-09-23	tsbarlowdds@hotmail.com	shipped	219135531	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-07 05:21:01	\N	Timothy S Barlow DDS	TIMOTHY S BARLOW DDS	515 KEISLER DR STE 204	\N	CARY	NC	27518-7097	US	(919) 859-5459	Timothy S Barlow DDS	\N	\N	\N	\N	\N	\N		(919) 859-5459	fedex	556346	fedex_ground	FedEx Ground	\N
192	100496	2025-09-23	\tFifth2thDr@AOL.com	shipped	219135171	3	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-07 05:21:01	\N	Timothy Harbolt	BROOKINGS DENTAL GROUP	565 5TH ST STE 2	\N	BROOKINGS	OR	97415-9724	US	(541) 469-5371	Timothy Harbolt	\N	\N	\N	\N	\N	\N		(541) 469-5371	fedex	556346	fedex_ground	FedEx Ground	\N
193	100498	2025-09-23	alivia@oracareproducts.com	shipped	219137879	17	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-07 05:21:01	\N	Alivia Webb	ORACARE	2000 INDUSTRIAL RD E STE 200	\N	BRIDGEPORT	WV	26330-1297	US	3046950642	Alivia Webb	\N	\N	\N	\N	\N	\N		3046950642	fedex	556346	fedex_ground	FedEx Ground	\N
194	685505	2025-09-23	vstokes@searhc.org	shipped	219336615	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Valerie Stokes	SEARHC WRANGELL DENTAL	232 WOOD STREET	\N	WRANGELL	AK	99929	US	(907) 660-7300	Valerie Stokes	SEARHC Wrangell Dental	232 WOOD STREET	\N	Wrangell	AK	99929	US	(907) 660-7300	fedex	556346	fedex_ground	FedEx Ground	\N
195	685515	2025-09-24	milfordohdental@gmail.com	shipped	219272673	6	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Steven Johnson	DENTAL WELLNESS OF MILFORD	1170 STATE ROUTE 28	\N	MILFORD	OH	45150-2155	US	(513) 575-9600	Steven Johnson	Dental Wellness of Milford	1170 St Rt 28	\N	Milford	OH	45150	US	(513) 575-9600	fedex	556346	fedex_ground	FedEx Ground	\N
196	685525	2025-09-24	inventory@coralgablesdentistry.com	shipped	219280679	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Laura Davila	CORAL GABLES DENTISTRY	3326 PONCE DE LEON BLVD	\N	CORAL GABLES	FL	33134-7211	US	(305) 567-1992	Laura Davila	coral gables dentistry	3326 PONCE DE LEON BLVD	\N	Coral Gables	FL	33134	US	(305) 567-1992	fedex	556346	fedex_ground	FedEx Ground	\N
197	685545	2025-09-24	Smiles@ADGTown.com	shipped	219288168	6	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Mark Duncan	AESTHETIC DENTISTRY OF GEORGETOWN	3622 WILLIAMS DR STE 2	\N	GEORGETOWN	TX	78628-2508	US	(512) 819-9100	Mark Duncan	Aesthetic Dentistry of Georgetown	2109 Commerce St\nSuite 200	\N	Dallas	TX	72501	US	5128199100	fedex	556346	fedex_ground	FedEx Ground	\N
198	685555	2025-09-24	drjordan@jordanfamilydentistry.net	shipped	219290983	2	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Sherrill Jordan	JORDAN FAMILY DENTISTRY	12180 HIGHWAY 601	\N	MIDLAND	NC	28107-9444	US	(704) 781-0094	Sherrill Jordan	Jordan Family Dentistry	12180 Highway 601 South	\N	Midland	NC	28107	US	(704) 781-0094	fedex	556346	fedex_ground	FedEx Ground	\N
199	685565	2025-09-24	DRGBM@AOL.COM	shipped	219299941	6	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Gregg Melfi	SYMMETRY DENTAL	1719 GAR HWY	\N	SWANSEA	MA	02777-3940	US	(508) 641-8260	Gregg Melfi	Symmetry Dental	1719 GAR Highway	\N	Swansea	MA	02777	US	(508) 641-8260	fedex	556346	fedex_ground	FedEx Ground	\N
200	685575	2025-09-24	ctaylor@smiledesigncenter.net	shipped	219336272	2	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Jeremy Manion	THE SMILE DESIGN CENTER	300 TOWNCENTER BLVD STE A	\N	TUSCALOOSA	AL	35406-1842	US	(205) 750-8008	Jeremy Manion	THE SMILE DESIGN CENTER	300 TOWNCENTER BLVD STE A	\N	TUSCALOOSA	AL	35406-1842	US	(205) 750-8008	fedex	556346	fedex_ground	FedEx Ground	\N
201	685585	2025-09-24	skylinefamily@comcast.net	shipped	219313028	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	ANGELA LYNN	SKYLINE FAMILY DENTAL CARE	3977 BURMA RD STE A	\N	MOBILE	AL	36693-4523	US	(251) 666-0576	ANGELA LYNN	SKYLINE FAMILY DENTAL CARE	3977 BURMA RD\nSUITE A	\N	Mobile	AL	36693	US	(251) 666-0576	fedex	556346	fedex_ground	FedEx Ground	\N
202	685595	2025-09-24	shannon@biodentsmile.com	shipped	219318229	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Shannon Browning	BIODENT SMILE	2221 CAMINO DEL RIO S STE 102	\N	SAN DIEGO	CA	92108-3609	US	(619) 231-1624	Shannon Browning	Biodent Smile	2221 camino del rio s Ste #102	\N	San Diego	CA	92108	US	(619) 231-1624	fedex	556346	fedex_ground	FedEx Ground	\N
203	685605	2025-09-24	info@northparkfamilydentistry.com	shipped	219330240	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Grace Scholl	NORTHPARK FAMILY DENTISTRY	1101 13TH ST N STE 1	\N	HUMBOLDT	IA	50548-1171	US	(515) 332-3230	Grace Scholl	Northpark Family Dentistry	1101 13th street north\nsuite 1	\N	humboldt	IA	50548	US	(515) 332-3230	fedex	556346	fedex_ground	FedEx Ground	\N
204	685615	2025-09-24	orders@zensupplies.com	shipped	219621187	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Ashkan Alizadeh	J STREET DENTAL GROUP	2619 J ST	\N	SACRAMENTO	CA	95816-4312	US	(916) 759-0238	Ashkan Alizadeh	J STREET DENTAL GROUP	2619 J ST	\N	SACRAMENTO	CA	95816-4312	US	9163914848	fedex	556346	fedex_ground	FedEx Ground	\N
205	685625	2025-09-24	lori@smilesnj.com	shipped	219354893	2	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Greggory Di Lauri	GREGGORY DI LAURI, DDS	66 SUNSET STRIP STE 307	\N	SUCCASUNNA	NJ	07876-1362	US	(973) 252-0030	Greggory Di Lauri	Greggory Di Lauri, DDS	66 Sunset Strip\nste 307	\N	Succasunna	NJ	07876	US	(973) 252-0030	fedex	556346	fedex_ground	FedEx Ground	\N
206	685635	2025-09-24	info@flsda.com	shipped	219357958	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	Fabiola Liendo	SAWGRASS DENTAL ARTS	11264 WILES RD	\N	CORAL SPRINGS	FL	33076-2111	US	(954) 757-6644	Fabiola Liendo	SAWGRASS DENTAL ARTS	11264 Wiles Road	\N	Coral Springs	FL	33076	US	(954) 757-6644	fedex	556346	fedex_ground	FedEx Ground	\N
207	685645	2025-09-24	elizabeth@mzdds.com	shipped	219621314	1	0	ShipStation Manual	2025-10-02 21:38:28	2025-10-03 17:42:12	\N	jonathan zsambeky	ZSAMBEKY,CHANEY AND ASSOCIATES. PA-TB	220 BRANCHVIEW DR SE	\N	CONCORD	NC	28025-3577	US	(704) 782-2214	jonathan zsambeky	ZSAMBEKY,CHANEY AND ASSOCIATES. PA-TB	220 BRANCHVIEW DR SE	\N	CONCORD	NC	28025-3577	US	(704) 782-2214	fedex	556346	fedex_ground	FedEx Ground	\N
208	685655	2025-09-24	info@icdsmiles.com	shipped	219369720	6	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	DeAndre Kirkendoll	CHAMPION DENTAL GROUP	8390 CHAMPIONS GT BLVD STE 314	\N	CHAMPIONS GT	FL	33896-8313	US	(407) 787-3892	DeAndre Kirkendoll	CHAMPION DENTAL GROUP	8390 CHAMPIONS GATE BLVD\nSTE 314	\N	CHAMPIONS GATE	FL	33896	US	(407) 787-3892	fedex	556346	fedex_ground	FedEx Ground	\N
209	685665	2025-09-24	jracanelli@lvstunningsmiles.com	shipped	219370985	6	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Richard Racanelli	STUNNING SMILES OF LAS VEGAS	6410 MEDICAL CENTER ST STE B	\N	LAS VEGAS	NV	89148-2401	US	7027360016	Richard Racanelli	Stunning Smiles of Las Vegas	6410 Medical Center St.\nsuite B	\N	Las Vegas	NV	89148	US	7027360016	fedex	556346	fedex_ground	FedEx Ground	\N
210	685675	2025-09-24	info@peakcitydentistry.com	shipped	219622525	1	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Christopher Tikvart	PEAK CITY FAMILY DENTISTRY	200 W CHATHAM ST	\N	APEX	NC	27502-1408	US	9193628797	Christopher Tikvart	PEAK CITY FAMILY DENTISTRY	200 W CHATHAM ST	\N	APEX	NC	27502-1408	US	9193628797	fedex	556346	fedex_ground	FedEx Ground	\N
211	685685	2025-09-24	frontdesk2@northidahodentalgroup.com	shipped	219382571	3	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	CHACE MICKELSON,	NORTH IDAHO DENTAL GROUP COEUR DB??ALENE	2165 N MERRITT CREEK LOOP	\N	COEUR D ALENE	ID	83814-4949	US	2086678282	Abbey Evans	North Idaho Dental Group	30336 Highway 200\nSuite A	\N	Ponderay	ID	83852	US	(208) 255-1255	fedex	556346	fedex_ground	FedEx Ground	\N
212	685705	2025-09-24	brezinski.matt@gmail.com	shipped	219399224	1	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Matthew Brezinski	BREZINSKI DENTAL LLC	801 N MAIN ST	\N	WASHINGTON	PA	15301-3347	US	(724) 222-1020	Matthew Brezinski	Brezinski Dental LLC	801 North Main Street	\N	Washington	PA	15301	US	(724) 222-1020	fedex	556346	fedex_ground	FedEx Ground	\N
213	685715	2025-09-24	glenbrook@kremerdental.com	shipped	219526400	6	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Kevin Kremer	KREMER DENTAL CARE	3 GLENBROOK CT	\N	CHICO	CA	95973-5402	US	(530) 892-1234	Kevin Kremer	Kremer Dental	6081 Grindstone Place	\N	Chico	CA	95973	US	530-892-1218	fedex	556346	fedex_ground	FedEx Ground	\N
214	685745	2025-09-24	aford@caleradentalcenter.com	shipped	219621163	1	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Deborah Rigsby Ashley Ford	CALERA DENTAL CENTER	101 HIGHWAY 87 BLDG 200	\N	CALERA	AL	35040-7203	US	(205) 620-3312	Deborah Rigsby	CALERA DENTAL CENTER	101 HIGHWAY 87 BLDG 200	\N	CALERA	AL	35040-7203	US	2056203312	fedex	556346	fedex_ground	FedEx Ground	\N
215	685755	2025-09-24	Scott.karafin@gmail.com	shipped	219531157	3	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Scott Karafin	SO CAL SMILES	22195 EL PASEO STE 220	\N	RCHO STA MARG	CA	92688-3952	US	(949) 766-0006	Scott Karafin	So Cal Smiles	22195 El Paseo\nste 220	\N	Ranch Santa Margarita	CA	92688	US	(949) 766-0006	fedex	556346	fedex_ground	FedEx Ground	\N
216	685765	2025-09-24	info@madisonvalleydentalcare.com	shipped	219531158	2	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Michelle Crabtree	SUMMIT DENTAL - ENNIS	1 STEAMBATH STE A	\N	ENNIS	MT	59729-8505	US	(406) 404-1186	William Samson	Summit Dental	3997 Valley Commons Drive	\N	Bozeman	MT	59718	US	406-404-1186	fedex	556346	fedex_ground	FedEx Ground	\N
217	685775	2025-09-24	mitalpateldds@gmail.com	shipped	219531159	4	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Mital Patel	MAGNOLIA FAMILY DENTAL	2561 3RD ST STE B	\N	CERES	CA	95307-3230	US	(209) 538-9297	Mital Patel	Magnolia Family Dental	533 rues rd	\N	Ripon	CA	95366	US	2095389297	fedex	556346	fedex_ground	FedEx Ground	\N
218	685785	2025-09-24	info@fielddentalcenter.com	shipped	219531160	1	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Stacy Mulholland	FIELD DENTAL CENTER	9475 BRIAR VILLAGE PT STE 310	\N	COLORADO SPGS	CO	80920-7905	US	(719) 598-0872	Stacy Mulholland	Field Dental Center	9475 Briar Village Point\nSuite #310	\N	Colorado Springs	CO	80920	US	(719) 598-0872	fedex	556346	fedex_ground	FedEx Ground	\N
219	685795	2025-09-24	tcookdds@sbcglobal.net	shipped	219531161	2	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Tracy Cook	CORAL BAY FAMILY DENTISTRY	1109 KENNEDY PL STE 1	\N	DAVIS	CA	95616-1271	US	530-753-2845	Tracy Cook	Coral Bay Family Dentistry	1109 Kennedy Pl\nSte 1	\N	Davis	CA	95616	US	530-753-2845	fedex	556346	fedex_ground	FedEx Ground	\N
220	685805	2025-09-24	hello@paloaltosmiles.com	shipped	219531162	3	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Ramtin Rastakhiz	PALO ALTO SMILES	2235 ALMA ST	\N	PALO ALTO	CA	94301-3905	US	(650) 327-1530	Ramtin Rastakhiz	Palo Alto Smiles	2235 Alma St.	\N	Palo Alto	CA	94301	US	(650) 327-1530	fedex	556346	fedex_ground	FedEx Ground	\N
221	685815	2025-09-24	lttaylor@mac.com	shipped	219531169	2	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Ryan Taylor	SWEETWATER DENTAL	1577 DEWAR DR STE 112	\N	ROCK SPRINGS	WY	82901-5716	US	(307) 382-2707	Ryan Taylor	Sweetwater Dental	1577 Dewar Dr.\nSte 112	\N	Rock Springs	WY	82901	US	(307) 382-2707	fedex	556346	fedex_ground	FedEx Ground	\N
222	685835	2025-09-24	andrewwchin@yahoo.com	shipped	219531946	5	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Andrew Chin	TRI CITY DENTAL CARE OF CERRITOS	18822 PALO VERDE AVE	\N	CERRITOS	CA	90703-9242	US	(562) 920-1731	Andrew Chin	tri city dental care of Cerritos	18822 Palo Verde Ave	\N	Cerritos	CA	90703	US	(562) 920-1731	fedex	556346	fedex_ground	FedEx Ground	\N
223	685845	2025-09-24	dumasorders@fullsmiledental.com	shipped	219531947	1	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Dr. Guzman	FULL SMILE DENTAL DUMAS	315 E 2ND ST	\N	DUMAS	TX	79029-3809	US	(806) 935-4161	Full Smile Management	Billing	2201 Civic Circle	\N	Amarillo	TX	79109	US	806-381-3435	fedex	556346	fedex_ground	FedEx Ground	\N
224	685855	2025-09-24	csheinrichs@houstondental.com	shipped	219532524	10	0	ShipStation Manual	2025-10-02 21:38:29	2025-10-03 17:42:12	\N	Amanda Canto	COSMETIC DENTIST OF HOUSTON	1900 WEST LOOP S STE 1150	\N	HOUSTON	TX	77027-3222	US	(713) 622-1977	Amanda Canto	Cosmetic Dentist of Houston	1900 West Loop South\nSuite 1150	\N	Houston	TX	77027	US	(713) 622-1977	fedex	556346	fedex_ground	FedEx Ground	\N
225	685865	2025-09-24	info@derekjchangdds.com	shipped	219532525	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Derek Chang	DEREK J. CHANG, DDS,	4758 MCARDLE RD STE 204	\N	CORP CHRISTI	TX	78411-4439	US	(361) 317-7350	Derek Chang	Derek J. Chang, DDS,	4758 McArdle Rd\nSuite 204	\N	Corpus Christi	TX	78411	US	(361) 317-7350	fedex	556346	fedex_ground	FedEx Ground	\N
226	685875	2025-09-24	contactus@precioussmilesfamilydentistry.com	shipped	219532526	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Precious McGregor-Wiltz	PRECIOUS SMILES FAMILY DENTISTRY	1041 BALCH RD STE 100	\N	MADISON	AL	35758-8821	US	(256) 434-5179	Precious McGregor-Wiltz	Precious Smiles Family Dentistry	1041 Balch Rd\nSte 100	\N	Madison	AL	35758	US	(256) 434-5179	fedex	556346	fedex_ground	FedEx Ground	\N
227	685885	2025-09-24	info@harborpointedental.com	shipped	219532528	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	David Ellsworth	HARBOR POINTE DENTAL	932 SPRING ST STE 102	\N	PETOSKEY	MI	49770-2286	US	(231) 347-8899	David Ellsworth	Harbor Pointe Dental	932 Springs St\nSte 102	\N	Petoskey	MI	49770	US	(231) 347-8899	fedex	556346	fedex_ground	FedEx Ground	\N
228	685895	2025-09-24	gmd77380@gmail.com	shipped	219532530	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Donna  Goodie	GROGANS MILL DENTAL	25210 GROGANS MILL RD STE A	\N	THE WOODLANDS	TX	77380-2380	US	(281) 298-5225	Donna  Goodie	Grogans Mill Dental	25210 Grogans Mill Rd	\N	The Woodlands	TX	77380	US	(281) 298-5225	fedex	556346	fedex_ground	FedEx Ground	\N
229	685905	2025-09-24	kdelamere22@hotmail.com	shipped	219532531	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Kim DeLamere	HIGH DESERT DENTAL	12212 W AMITY RD	\N	BOISE	ID	83709-5389	US	(208) 343-4732	Kim DeLamere	High Desert Dental	12212 W Amity Rd	\N	Boise	ID	83709	US	(208) 343-4732	fedex	556346	fedex_ground	FedEx Ground	\N
230	685915	2025-09-24	info@swd.care	shipped	219532532	2	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Tim Messer	SOUTHWIND DENTAL CARE	7842 PLAYERS CLUB PKWY W	\N	MEMPHIS	TN	38119-9168	US	(901) 751-1260	Tim Messer	Southwind Dental Care	7842 Players Club Pkwy W.	\N	Memphis	TN	38119	US	(901) 751-1260	fedex	556346	fedex_ground	FedEx Ground	\N
231	685925	2025-09-24	chad@tncld.com	shipped	219533172	5	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Chad Edwards	TENNESSEE CENTERS FOR LASER DENTISTRY	204 MILLERSPRINGS CT STE 200	\N	FRANKLIN	TN	37064-5432	US	615-595-8070	Chad Edwards	Tennessee Centers for Laser Dentistry	3046 Columbia Ave\nSuite 201	\N	Franklin	TN	37064	US	(615) 595-8070	fedex	556346	fedex_ground	FedEx Ground	\N
232	685935	2025-09-24	Fdesk@dentaloffice.com	shipped	219533174	3	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Shirley Matthew	CREEKVIEW FAMILY DENTISTRY	860 HEBRON PKWY STE 902	\N	LEWISVILLE	TX	75057-5145	US	(972) 459-1100	Shirley Matthew	Creekview Family Dentistry	860 Hebron Pkwy\nSuite 902	\N	Lewisville	TX	75057	US	(972) 459-1100	fedex	556346	fedex_ground	FedEx Ground	\N
233	685945	2025-09-24	adminassistant@gps.dental	shipped	219533175	6	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Jeffrey Hubbard	PARK CITIES FAMILY DENTISTRY	4131 N CENTRAL EXPY STE 600	\N	DALLAS	TX	75204-2174	US	(214) 528-3770	Jeffrey Hubbard	Park Cities Family Dentistry	PO 17151	\N	Jonesboro	AR	72403	US	214-528-3770	fedex	556346	fedex_ground	FedEx Ground	\N
234	685955	2025-09-24	springfieldsmiles@yahoo.com	shipped	219533177	2	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Christian Victor	SPRINGFIELD SMILES	1980 KINGSGATE RD STE A	\N	SPRINGFIELD	OH	45502-8226	US	(937) 390-3077	Christian Victor	Springfield Smiles	1980 Kingsgate Rd\nSte A	\N	Springfield	OH	45502	US	(937) 390-3077	fedex	556346	fedex_ground	FedEx Ground	\N
235	685965	2025-09-24	warnerplazadentalgroup@gmail.com	shipped	219533179	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Azin Kolahi	WARNER PLAZA DENTAL GROUP	5989 TOPANGA CANYON BLVD	\N	WOODLAND HLS	CA	91367-3623	US	(818) 888-6700	Azin Kolahi	Warner Plaza Dental Group	940 Bluegrass Ln	\N	Los angeles	CA	90049	US	3106004550	fedex	556346	fedex_ground	FedEx Ground	\N
236	685975	2025-09-24	kyle.bogan@gmail.com	shipped	219533180	5	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Kyle Bogan	NORTH ORANGE FAMILY DENTISTRY	7325 GOODING BLVD	\N	DELAWARE	OH	43015-7086	US	(740) 548-1800	Kyle Bogan	North Orange Family Dentistry	7325 Gooding Blvd	\N	Delaware	OH	43015	US	(740) 548-1800	fedex	556346	fedex_ground	FedEx Ground	\N
237	685985	2025-09-24	mysmilecraft@gmail.com	shipped	219533182	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Amy Nguyen	SMILE CRAFT DENTAL INC.	787 E EL CAMINO REAL	\N	SUNNYVALE	CA	94087-2919	US	650-967-9900	Amy Nguyen	Smile Craft Dental- Mountain View	16 Bronte Street	\N	San Francisco	CA	94110	US	6509679900	fedex	556346	fedex_ground	FedEx Ground	\N
238	685995	2025-09-24	contactus@altadentalofmaine.com	shipped	219533184	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Jospeh Wetherhold	ALTA DENTAL OF MAINE	348 US ROUTE 1	\N	FREEPORT	ME	04032-7016	US	(207) 865-1900	Jospeh Wetherhold	Alta Dental of Maine	348 US Route 1	\N	Freeport	ME	04032	US	(207) 865-1900	fedex	556346	fedex_ground	FedEx Ground	\N
239	686005	2025-09-24	kalexanderdmd@gmail.com	shipped	219533186	6	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Alexander Dentistry	ALEXANDER DENTISTRY	48 CHURCH ST	\N	MOUNTAIN BRK	AL	35213-3744	US	(205) 871-7361	Alexander Dentistry	Alexander Dentistry	48 Church Street	\N	Mountain Brook	AL	35213	US	(205) 871-7361	fedex	556346	fedex_ground	FedEx Ground	\N
240	686015	2025-09-24	lab@ccfdmail.com	shipped	219534424	20	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Aaron Wilharm	COASTAL COSMETIC FAMILY DENTISTRY	3071 SOUTHPORT SUPPLY RD SE	\N	BOLIVIA	NC	28422-7943	US	910-253-0000	Aaron Wilharm	Coastal Cosmetic Family Dentistry	3071 southport-supply rd	\N	Bolivia	NC	28422	US	910-253-0000	fedex	556346	fedex_ground	FedEx Ground	\N
241	686025	2025-09-24	deb@lakedentalassociates.com	shipped	219534426	6	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Deb Weiland	LAKE DENTAL ASSOCIATES	102 N 5TH ST	\N	CLEAR LAKE	IA	50428-1803	US	(641) 357-4112	Deb Weiland	Lake Dental Associates	102 N 5th St.	\N	Clear Lake	IA	50428	US	(641) 357-4112	fedex	556346	fedex_ground	FedEx Ground	\N
242	686035	2025-09-24	info@renewdentalarts.com	shipped	219534428	3	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Madison Shuee	RENEW DENTAL ARTS	2205 N DELAWARE ST STE 103	\N	INDIANAPOLIS	IN	46205-4363	US	(317) 602-8924	Madison Shuee	Renew Dental Arts	2205 N Delaware Street	\N	Indianapolis	IN	46205	US	(317) 602-8924	fedex	556346	fedex_ground	FedEx Ground	\N
243	686055	2025-09-24	kyle.dumpert@gmail.com	shipped	219534430	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Kyle Dumpert	RADIANT DENTAL OF BEDFORD	902 ECHO VALE DR	\N	BEDFORD	PA	15522-2010	US	(814) 623-2217	Kyle Dumpert	Radiant Dental of Bedford	902 Echo Vale Drive	\N	Bedford	PA	15522	US	(814) 623-2217	fedex	556346	fedex_ground	FedEx Ground	\N
244	686085	2025-09-24	info@daltonhuntdentistry.com	shipped	219536187	2	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Dalton Carruthers Hunt	DR. DALTON CARRUTHERS HUNT, DMD	3600 HAWORTH DR STE 1	\N	RALEIGH	NC	27609-7225	US	919-787-8243	Dalton Carruthers Hunt	Dr. Dalton Carruthers Hunt, DMD	3600 Haworth Drive\nSuite 1	\N	Raleigh	NC	27609	US	919-787-8243	fedex	556346	fedex_ground	FedEx Ground	\N
245	686095	2025-09-25	office@woodburyfamilydentists.com	shipped	219555173	1	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Stacey Wigley	WOODBURY FAMILY DENTISTS	8375 CITY CENTRE DR	\N	WOODBURY	MN	55125-3604	US	(651) 731-8424	Stacey Wigley	Woodbury Family Dentists	8375 City Centre Drive	\N	woodbury	MN	55125	US	(651) 731-8424	fedex	556346	fedex_ground	FedEx Ground	\N
246	686105	2025-09-25	info@lindseyfamilydental.com	shipped	219555176	3	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Ashley Hill	LINDSEY FAMILY DENTAL	480 HANCOCK ST	\N	MADISON	GA	30650-1343	US	(706) 342-2155	Ashley Hill	Lindsey Family Dental	480 Hancock St	\N	Madison	GA	30650	US	(706) 342-2155	fedex	556346	fedex_ground	FedEx Ground	\N
247	686115	2025-09-25	smile@laudenbach.com	shipped	219567509	6	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Jay Laudenbach	LAUDENBACH PERIODONTICS & DENTAL IMPLANTS	1520 LOCUST ST STE 600	\N	PHILADELPHIA	PA	19102-4406	US	(215) 985-4337	Jay Laudenbach	Laudenbach Periodontics & Dental Implants	1520 Locust St \n#600	\N	Philadelphia	PA	19102	US	(215) 985-4337	fedex	556346	fedex_ground	FedEx Ground	\N
248	686125	2025-09-25	drmikemusso@gmail.com	shipped	219568949	6	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Mike & Mark Musso	MUSSO FAMILY DENTISTRY	513 W CENTERVILLE RD	\N	GARLAND	TX	75041-5445	US	(972) 840-8477	Mike & Mark Musso	Musso Family Dentistry	513 W Centerville Road	\N	Garland	TX	75041	US	(972) 840-8477	fedex	556346	fedex_ground	FedEx Ground	\N
249	686135	2025-09-25	mscruzrdh@aol.com	shipped	219571019	6	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Rebecca Cruz	AMAZING SMILES	16532 OAK PARK AVE STE 200	\N	TINLEY PARK	IL	60477-2273	US	(708) 444-7645	Rebecca Cruz	Amazing Smiles	16532 Oak Park Ave\nSte 200	\N	Tinley Park	IL	60452	US	(708) 444-7645	fedex	556346	fedex_ground	FedEx Ground	\N
250	686145	2025-09-25	michelle@pineridgedentists.com	shipped	219576386	6	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Michelle Nelson	PINE RIDGE DENTAL	541 MAIN ST	\N	LONGMONT	CO	80501-5607	US	(303) 776-3030	Michelle Nelson	Pine Ridge Dental	541 Main St	\N	Longmont	CO	80501	US	(303) 776-3030	fedex	556346	fedex_ground	FedEx Ground	\N
251	686155	2025-09-25	info@massaridentistry.com	shipped	219577422	6	0	ShipStation Manual	2025-10-02 21:38:30	2025-10-03 17:42:12	\N	Jessica Massari	MASSARI DENTISTRY AND AESTHETICS	29160 CENTER RIDGE RD STE K	\N	WESTLAKE	OH	44145-5258	US	(440) 331-1854	Jessica Massari	Massari Dentistry and Aesthetics	29160 Center Ridge Road\nSte k	\N	Westlake	OH	44145	US	(440) 331-1854	fedex	556346	fedex_ground	FedEx Ground	\N
252	686165	2025-09-25	sinabeta@yahoo.com	shipped	219577423	3	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Scott Nabeta	PENINSULA SMILES/SCOTT NABETA, DDS	425 BURGESS DR	\N	MENLO PARK	CA	94025-3408	US	(650) 321-0915	Scott Nabeta	Peninsula Smiles/Scott Nabeta, DDS	425 Burgess Dr.	\N	Menlo Park	CA	94025	US	(650) 321-0915	fedex	556346	fedex_ground	FedEx Ground	\N
253	686175	2025-09-25	info@bacliffdental.com	shipped	219579085	1	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Craig  McGregor	BACLIFF DENTAL	235 GRAND AVE	\N	BACLIFF	TX	77518-1609	US	(281) 559-1531	Craig  McGregor	Bacliff Dental	235 Grand Ave	\N	Bacliff	TX	77518	US	(281) 559-1531	fedex	556346	fedex_ground	FedEx Ground	\N
254	686185	2025-09-25	drcaleb@cardds.com	shipped	219580672	6	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Caleb Robinson	CALEB A ROBINSON, DDS	541 WABASH AVE NW	\N	NEW PHILA	OH	44663-4143	US	(614) 352-5653	Caleb Robinson	Caleb A Robinson, DDS	541 Wabash Ave NW	\N	New Philadelphia	OH	44663	US	(614) 352-5653	fedex	556346	fedex_ground	FedEx Ground	\N
255	686195	2025-09-25	christymboudreaux@gmail.com	shipped	219591900	6	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Christy Boudreaux	BOUDREAUX DENTAL GROUP	175 LEE ST	\N	LUMBERTON	TX	77657-7577	US	(409) 755-6565	Christy Boudreaux	Boudreaux Dental Group	175 Lee St	\N	Lumberton	TX	77657	US	(409) 755-6565	fedex	556346	fedex_ground	FedEx Ground	\N
256	686215	2025-09-25	contactus@schafferdental.com	shipped	219598570	6	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Laurie Breier	SCHAFFER DENTAL EXCELLENCE	12750 CARMEL CNTRY RD STE 205	\N	SAN DIEGO	CA	92130-2171	US	(619) 208-4661	Billing Billing	Billing	16220 North Scottdale Road\nSte 300	\N	Scottsdale	AZ	85254	US	858-481-1148	fedex	556346	fedex_ground	FedEx Ground	\N
257	686225	2025-09-25	harmonfamilydental@gmail.com	shipped	219603137	6	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Steve Harmon	HARMON FAMILY DENTAL	1151 GATEWAY BLVD STE 102	\N	ROCK SPRINGS	WY	82901-6771	US	(307) 382-5909	Steve Harmon	HARMON FAMILY DENTAL	STEVE HARMON DDS\n1151 GATEWAY BLVD STE 102	\N	ROCK SPRINGS	WY	82901	US	(307) 382-5909	fedex	556346	fedex_ground	FedEx Ground	\N
258	686235	2025-09-25	contactus@schafferdental.com	shipped	219607404	1	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Laurie Breier	SCHAFFER DENTAL EXCELLENCE	12750 CARMEL CNTRY RD STE 205	\N	SAN DIEGO	CA	92130-2171	US	(619) 208-4661	Billing Billing	Billing	16220 North Scottdale Road\nSte 300	\N	Scottsdale	AZ	85254	US	858-481-1148	fedex	556346	fedex_ground	FedEx Ground	\N
259	686245	2025-09-25	castlefamilydentistry@gmail.com	shipped	219621002	1	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Brian Bialiy	CASTLE FAMILY DENTISTRY, LLC	413 NJ-57,	\N	WASHINGTON	NJ	07882-2191	US	9086890911	Brian Bialiy	Castle Family Dentistry, LLC	413 NJ-57	\N	Washington	NJ	07882	US	9086890911	fedex	556346	fedex_ground	FedEx Ground	\N
260	686265	2025-09-25	scevilledentistry@gmail.com	shipped	219644375	2	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Jeff Sceville	SCEVILLE DENTISTRY	1390 W H ST STE D	\N	OAKDALE	CA	95361-3529	US	(209) 847-8091	Jeff Sceville	Sceville Dentistry	1390 W H St D	\N	Oakdale	CA	95361	US	(209) 847-8091	fedex	556346	fedex_ground	FedEx Ground	\N
261	686275	2025-09-25	tustin@timkimdental.com	shipped	219647952	5	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Keon Jung Kim	KEON JUNG KIM PROFESSIONAL DENTAL CORP	2492 WALNUT AVE STE 200	\N	TUSTIN	CA	92780-6960	US	949-679-6000	Keon Jung Kim	Keon Jung Kim Professional Dental Corp	2492 Walnut Ave\nSte 200	\N	Tustin	CA	92780	US	949-679-6000	fedex	556346	fedex_ground	FedEx Ground	\N
262	686315	2025-09-25	proaksdental@gmail.com	shipped	219661358	1	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Brady Robles	OAKS DENTAL GROUP	2727 BUENA VISTA DR STE 110	\N	PASO ROBLES	CA	93446-8581	US	(805) 238-1118	Brady Robles	Oaks Dental Group	2727 Beuno Vista Drive\nSuite 110	\N	Paso Robles	CA	93446	US	(805) 238-1118	fedex	556346	fedex_ground	FedEx Ground	\N
263	686325	2025-09-25	rick.downs3430@gmail.com	shipped	219665097	1	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Mark Schwartzhoff	RICHARD D. DOWNS, D.D.S., P.C.	411 E 200 THIRD ST	\N	BELTON	MO	64012	US	(563) 590-1563	Mark Schwartzhoff	Richard D. Downs, D.D.S., P.C.	3280 Lake Front Drive	\N	Dubuque	IA	52003	US	(563) 590-1563	fedex	556346	fedex_ground	FedEx Ground	\N
264	686365	2025-09-25	info@tuscaroradental.com	shipped	219667733	2	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Angelina  Browning	TUSCARORA FAMILY DENTAL CARE	22 SIERRA DR	\N	MARTINSBURG	WV	25403-1133	US	(304) 263-3131	Angelina  Browning	Tuscarora Family Dental Care	22 Sierra Drive	\N	Martinsburg	WV	25403	US	(304) 263-3131	fedex	556346	fedex_ground	FedEx Ground	\N
265	686385	2025-09-25	suarezdental@gmail.com	shipped	219677027	2	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Henry Suarez	HEALTHY DENTAL EXPRESSIONS	3960 HYPOLUXO RD STE 101	\N	BOYNTON BEACH	FL	33436-8534	US	5619692696	Henry Suarez	Healthy Dental Expressions	3960 Hypoluxo Road\nsuite 101	\N	Boynton Beach	FL	33436	US	5619692696	fedex	556346	fedex_ground	FedEx Ground	\N
266	686415	2025-09-25	Longmontbackoffice@FoxCreekFamilyDental.Com	shipped	219682811	1	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	RYAN KOENIG	FOX CREEK FAMILY DENTAL (LONGMONT)	1610 PACE ST UNIT 100	\N	LONGMONT	CO	80504-2239	US	(303) 772-9966	RYAN KOENIG	Fox Creek Dental	2818 Shoshoney Trail	\N	Lafayette	CO	80026	US	9709888152	fedex	556346	fedex_ground	FedEx Ground	\N
267	686425	2025-09-25	staff@lauramanueldds.com	shipped	219685427	6	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Laura Manuel	NAPLES DENTAL CARE	5580 E 2ND ST STE 201	\N	LONG BEACH	CA	90803-3959	US	(562) 433-6735	Laura Manuel	Naples Dental Care	5580 E. Second Street\nSte 201	\N	Long Beach	CA	90803	US	(562) 433-6735	fedex	556346	fedex_ground	FedEx Ground	\N
268	100499	2025-09-25		shipped	219576123	2	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-07 05:21:01	\N	Dac Nguyen	Clinique Dentaire Dac	550-4141 Sherbrooke St W	\N	Westmount	QC	H3Z 1B8	CA	\N	Dac Nguyen	\N	\N	\N	\N	\N	\N		\N	fedex	556346	fedex_ground_international	Fedex Ground International	\N
269	686445	2025-09-25	rdh@campidental.com	shipped	219892964	2	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	John Campi	CAMPIDENTAL	2041 HIGHWAY 35	\N	WALL TOWNSHIP	NJ	07719-3506	US	(732) 449-2228	John Campi	CampiDental	2041 Highway 35	\N	WALL TOWNSHIP	NJ	07719	US	(732) 449-2228	fedex	556346	fedex_ground	FedEx Ground	\N
270	100500	2025-09-25	shawneemoderndentistry@smilegeneration.com	shipped	219587646	1	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-07 05:21:01	\N	Pardeep Gill	SHAWNEE MODERN DENTISTRY	15834 SHAWNEE MISSION PKWY	\N	SHAWNEE	KS	66217-9326	US	913-631-0866	Pardeep Gill	\N	\N	\N	\N	\N	\N		913-631-0866	fedex	556346	fedex_ground	FedEx Ground	\N
271	686455	2025-09-25	berdjk@aol.com	shipped	219892966	3	0	ShipStation Manual	2025-10-02 21:38:31	2025-10-03 17:42:12	\N	Berdj Kaladjian	LONGWOOD DENTAL GROUP	1842 BEACON ST	\N	BROOKLINE	MA	02445-1900	US	(617) 566-5445	Berdj Kaladjian	Longwood Dental group	1842 Beacon St.	\N	Brookline	MA	02445	US	(617) 566-5445	fedex	556346	fedex_ground	FedEx Ground	\N
272	686465	2025-09-25	reid.dentistry@gmail.com	shipped	219892967	6	0	ShipStation Manual	2025-10-02 21:38:32	2025-10-03 17:42:12	\N	Douglas Reid	REIDEFINE SMILES	6600 LBJ FWY STE 225	\N	DALLAS	TX	75240-6547	US	(925) 398-3975	Douglas Reid	Reidefine Smiles	4517 Reiger Ave	\N	Dallas	TX	75246	US	(925) 398-3975	fedex	556346	fedex_ground	FedEx Ground	\N
273	686485	2025-09-25	birchfamilydentistrywy@gmail.com	shipped	219892968	1	0	ShipStation Manual	2025-10-02 21:38:32	2025-10-03 17:42:12	\N	Charity Clark	BIRCH FAMILY DENTISTRY	661 UINTA DR STE A	\N	GREEN RIVER	WY	82935-5056	US	(307) 875-3658	Charity Clark	Birch Family Dentistry	661 Uinta Drive	\N	Green River	WY	82935	US	(307) 875-3658	fedex	556346	fedex_ground	FedEx Ground	\N
274	100501	2025-09-25	mgardner@stardentalpartners.com	shipped	219963558	1	0	ShipStation Manual	2025-10-02 21:38:32	2025-10-03 17:42:12	\N	Ron S. White, DDS	RON S. WHITE, DDS	4189 EAST US-290	\N	DRIPPING SPRINGS	TX	78620	US	\N	Ron S. White, DDS	Ron S. White, DDS	4189 EAST HWY	\N	Dripping Springs	TX	78620	US	\N	fedex	556346	fedex_ground	FedEx Ground	\N
275	100502	2025-09-29	newmarkmoderndentistry@smilegeneration.com	shipped	220563105	6	0	ShipStation Manual	2025-10-02 21:38:32	2025-10-07 05:21:01	\N	Frankie Barnhart	NEW MARK MODERN DENTISTRY	9350 N OAK TRFY	\N	KANSAS CITY	MO	64155-2263	US	816-400-4045	Frankie Barnhart	\N	\N	\N	\N	\N	\N		816-400-4045	fedex	556346	fedex_ground	FedEx Ground	\N
276	100503	2025-09-29	ericbordleedds@gmail.com	shipped	220600499	1	0	ShipStation Manual	2025-10-02 21:38:32	2025-10-07 05:21:01	\N	Eric Bordlee	BORDLEE FAMILY AND COSMETIC DENTISTRY	6204 RIDGE AVE	\N	CINCINNATI	OH	45213-1316	US	(513) 731-1106	Eric Bordlee	\N	\N	\N	\N	\N	\N		(513) 731-1106	fedex	556346	fedex_ground	FedEx Ground	\N
454	689555	2025-10-10	sanantonio6bf@pacden.com	cancelled	224351400	6	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Oscar DeLeon	Potranco Dentistry- PacDen	10538 Potranco Rd\nSte 206	\N	San Antonio	TX	78251	US	(210) 469-4235	Oscar DeLeon	Potranco Dentistry- PacDen	10538 Potranco Rd\nSte 206	\N	San Antonio	TX	78251	US	(210) 469-4235	fedex	556346	fedex_ground	FedEx Ground	\N
634	100534	2025-10-15	RainesM@nadentalgroup.com	shipped	225143086	2	0	ShipStation Manual	2025-10-15 21:13:44.144495	2025-10-16 17:09:25.280453	\N	Makenli Raines	NORTHPOINT DENTAL CO	1963 NORTHPOINT BLVD STE 113	\N	HIXSON	TN	37343-4638	US	423-894-5223	Makenli Raines	\N	\N	\N	\N	\N	\N	\N	423-894-5223	fedex	556346	fedex_ground	FedEx Ground	\N
633	100533	2025-10-15	mikkah@oracareproducts.com	shipped	225097312	2	0	ShipStation Manual	2025-10-15 21:13:44.144495	2025-10-16 17:09:39.064119	\N	Summit Dental Group	SUMMIT DENTAL GROUP	782 S AMERICANA BLVD	\N	BOISE	ID	83702-6733	US	3049184302	Summit Dental Group	\N	\N	\N	\N	\N	\N	\N	3049184302	fedex	556346	fedex_ground	FedEx Ground	\N
449	689495	2025-10-10	jswinson@dentistsofalbuquerque.com	shipped	224351382	15	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Davis Gribble	Davis Gribble Hollowwa Dental	3610 Calle Cuervo NW	\N	Albuquerque	NM	87114	US	(505) 898-1976	Davis Gribble	Davis Gribble Hollowwa Dental	3610 Calle Cuervo NW	\N	Albuquerque	NM	87114	US	(505) 898-1976	fedex	556346	fedex_ground	FedEx Ground	\N
450	689505	2025-10-10	info@willettdentalassociates.com	shipped	224358136	2	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Michelle Simonsen	Willett Dental Associates	1601 Chapel Hill Rd\nSte C	\N	Columbia	MO	65203	US	(573) 445-5200	Michelle Simonsen	Willett Dental Associates	1601 Chapel Hill Rd\nSte C	\N	Columbia	MO	65203	US	(573) 445-5200	fedex	556346	fedex_ground	FedEx Ground	\N
452	689525	2025-10-10	overlandparkmoderndentistry@smilegeneration.co	cancelled	224351391	3	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Michelle Ralph	Overland Park Modern Dentistry	13316 Metcalf Ave	\N	13316 Metcalf Ave	KS	66213	US	(913) 851-5110	Michelle Ralph	Overland Park Modern Dentistry	13316 Metcalf Ave	\N	13316 Metcalf Ave	KS	66213	US	(913) 851-5110	fedex	556346	fedex_ground	FedEx Ground	\N
417	689325	2025-10-09	OFFICE@OAKRIDGEDENTALSMILES.COM	shipped	223323308	15	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 14:50:25.126422	\N	Brian Call	OAKRIDGE DENTAL	1838 N 1075 W, Suite 200	\N	FARMINGTON	UT	84025	US	(801) 451-6222	Brian Call	OAKRIDGE DENTAL	1838 N 1075 W, Suite 200	\N	FARMINGTON	UT	84025	US	(801) 451-6222	fedex	556346	fedex_ground	FedEx Ground	\N
418	689335	2025-10-09	mirandahansen22@yahoo.com	shipped	223324558	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 14:50:25.126422	\N	Miranda Hansen	Dr. Lance Johnson Family Dentistry	3333 N FM1417	\N	Sherman	TX	75092	US	(903) 893-2540	Miranda Hansen	Dr. Lance Johnson Family Dentistry	3333 N FM1417	\N	Sherman	TX	75092	US	(903) 893-2540	fedex	556346	fedex_ground	FedEx Ground	\N
419	689345	2025-10-09	info@fremontgreenhillsdental.com	shipped	223343932	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 14:50:25.126422	\N	Shirley Bien	Shirley H Bien DMD Inc	39560 Stevenson Pl \nSuite 212	\N	Fremont	CA	94539	US	510-790-8800	Shirley Bien	Shirley H Bien DMD Inc	39560 Stevenson Pl \nSuite 212	\N	Fremont	CA	94539	US	510-790-8800	fedex	556346	fedex_ground	FedEx Ground	\N
420	689385	2025-10-09	smilemaker@san.rr.com	shipped	223415095	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 18:06:26.449834	\N	david sabourin	david a sabourin dds	9850 genesee ave. suite 760\nsuite 760	\N	la jolla	CA	92037	US	(858) 452-2333	david sabourin	david a sabourin dds	9850 genesee ave. suite 760\nsuite 760	\N	la jolla	CA	92037	US	(858) 452-2333	fedex	556346	fedex_ground	FedEx Ground	\N
421	689395	2025-10-09	fuscdent@yahoo.com	shipped	223417928	15	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 18:06:26.449834	\N	Adam Fusco	Adam D. Fusco DMD	168 N Victor Way	\N	Crossville	TN	38555	US	(931) 267-3472	Adam Fusco	Adam D. Fusco DMD	168 N Victor Way	\N	Crossville	TN	38555	US	(931) 267-3472	fedex	556346	fedex_ground	FedEx Ground	\N
457	689585	2025-10-13	ndtayari@gmail.com	shipped	224366297	1	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Nadia Taiyari	Nadia Taiyari	2212 Sam Rayburn Hwy #300	\N	Melissa	TX	75454	US	(972) 837-2929	Nadia Taiyari	Nadia Taiyari	2212 Sam Rayburn Hwy #300	\N	Melissa	TX	75454	US	(972) 837-2929	fedex	556346	fedex_ground	FedEx Ground	\N
458	689595	2025-10-13	Olive2467@gmail.com	shipped	224379969	1	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Christian Nwokorie	Christian Family Dentistry	2100 S reeves Road	\N	Decantur	TX	76234	US	(940) 627-8400	Christian Nwokorie	Christian Family Dentistry	1813 Goldenrod Lane	\N	Keller	TX	76248	US	3474398901	fedex	556346	fedex_ground	FedEx Ground	\N
459	689605	2025-10-13	frontdesk2@northidahodentalgroup.com	shipped	224393804	6	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	CHACE MICKELSON,	North Idaho Dental Group Coeur dâAlene	2165 N. Merritt Creek Loop	\N	Coeur dâAlene	ID	83814	US	2086678282	Abbey Evans	North Idaho Dental Group	30336 Highway 200\nSuite A	\N	Ponderay	ID	83852	US	(208) 255-1255	fedex	556346	fedex_ground	FedEx Ground	\N
448	689485	2025-10-10	jennifer@asd-austin.com	shipped	224351377	15	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Jennifer Laubach	advanced smiles dental	8715 W. Parmer Ln. Bldg 2\nSUITE 100	\N	Austin	TX	78729	US	(512) 258-3384	Jennifer Laubach	advanced smiles dental	8715 W. Parmer Ln. Bldg 2\nSUITE 100	\N	Austin	TX	78729	US	(512) 258-3384	fedex	556346	fedex_ground	FedEx Ground	\N
476	689795	2025-10-13	Heather@Pearlywhites4life.com	shipped	224520182	1	\N	X-Cart	2025-10-13 20:29:19	2025-10-16 17:27:39.325556	\N	Heather Parkhurst	Claremont Dental Arts	3034 N Oxford St.	\N	Claremont	NC	28610	US	(828) 459-1990	Heather Parkhurst	Claremont Dental Arts	3034 N Oxford St.	\N	Claremont	NC	28610	US	(828) 459-1990	fedex	556346	fedex_ground	FedEx Ground	\N
566	690385	2025-10-15	lcbrislindentistry@yahoo.com	shipped	225003323	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Lindsay Brislin	Lindsay Brislin Dentistry	536 Central Avenue	\N	Pawtucket	RI	02861	US	(401) 726-1772	Lindsay Brislin	Lindsay Brislin Dentistry	120 West Barn Road	\N	North Attleboro	MA	02760	US	401-726-1772	fedex	556346	fedex_ground	FedEx Ground	\N
567	690395	2025-10-15	Cameowrfd@comcast.net	shipped	225003324	5	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Dennis Pierce	White River Family Dental	1638 W Smith Valley Rd Ste B	\N	Greenwood	IN	46142	US	(317) 881-4726	Dennis Pierce	White River Family Dental	1638 W Smith Valley Rd Ste B	\N	Greenwood	IN	46142	US	(317) 881-4726	fedex	556346	fedex_ground	FedEx Ground	\N
568	690405	2025-10-15	jlai@edgedentalhouston.com	shipped	225003326	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Justin Lai	Edge Dental	15455 Memorial Dr\nSte 400 Edge Dental	\N	HOUSTON	TX	77079	US	(281) 940-8940	Justin Lai	Edge Dental	15455 Memorial Dr\nSte 400 Edge Dental	\N	HOUSTON	TX	77079	US	(281) 940-8940	fedex	556346	fedex_ground	FedEx Ground	\N
569	690415	2025-10-15	pdelriodds@gmail.com	shipped	225003328	3	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Paulina Del Rio	Del Rio Dental Studio	22304 Main St	\N	Hayward	CA	94541	US	(510) 886-5400	Paulina Del Rio	Del Rio Dental Studio	27750 Fallen Leaf Court	\N	Hayward	CA	94542	US	5108477594	fedex	556346	fedex_ground	FedEx Ground	\N
570	690425	2025-10-15	contactus@allansthomas.com	shipped	225003334	7	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Allan Thomas	Thomas Dental	2545 E Parleys Way\nSte D	\N	Salt Lake City	UT	84109	US	(801) 322-4900	Allan Thomas	Thomas Dental	2545 E Parleys Way\nSte D	\N	Salt Lake City	UT	84109	US	(801) 322-4900	fedex	556346	fedex_ground	FedEx Ground	\N
571	690435	2025-10-15	katelynbogus@singingriverdentistry.net	shipped	225004497	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Ryan Eaton	Singing River - Muscle Shoals	2402 Avalon Ave\nSuite A	\N	Muscle Shoals	AL	35661	US	(256) 383-1112	Ryan Eaton	Singing River - Muscle Shoals	2402 Avalon Ave\nSuite A	\N	Muscle Shoals	AL	35661	US	(256) 383-1112	fedex	556346	fedex_ground	FedEx Ground	\N
572	690445	2025-10-15	info@northbridge-dental.com	shipped	225004501	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Jenna Windell	Crosscreek Dental	1300 Old Highway 135 NE	\N	Corydon	IN	47112	US	(812) 738-8081	Jenna Windell	Crosscreek Dental	1300 Old Highway 135 NE	\N	Corydon	IN	47112	US	(812) 738-8081	fedex	556346	fedex_ground	FedEx Ground	\N
640	691005	2025-10-16	brooklinedentalassociates19083@gmail.com	shipped	225293280	6	\N	X-Cart	2025-10-16 13:29:22.131643	2025-10-16 17:27:39.325556	\N	Anh Tran	Brookline Dental Associates	40 Brookline Blvd	\N	Havertown	PA	19083	US	(610) 446-4225	Anh Tran	Brookline Dental Associates	40 Brookline Blvd	\N	Havertown	PA	19083	US	(610) 446-4225	fedex	556346	fedex_ground	FedEx Ground	\N
642	691035	2025-10-16	info@dentistryofthepines.com	shipped	225300112	15	\N	X-Cart	2025-10-16 14:01:09.68142	2025-10-16 17:27:39.325556	\N	Jason Graves	Dentistry of The Pines	100 Pavilion Way \nSte G	\N	Southern Pines	NC	28387	US	(910) 684-3687	Jason Graves	Dentistry of The Pines	100 Pavilion Way \nSte G	\N	Southern Pines	NC	28387	US	(910) 684-3687	fedex	556346	fedex_ground	FedEx Ground	\N
461	689625	2025-10-13	treatment@hannibaldentist.com	shipped	224405464	1	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Michael McKenzie	McKenzie Family Dentistry	9195 Hwy W	\N	Hannibal	MO	63401	US	(573) 221-0440	Michael McKenzie	McKenzie Family Dentistry	9195 Hwy W	\N	Hannibal	MO	63401	US	(573) 221-0440	fedex	556346	fedex_ground	FedEx Ground	\N
462	689635	2025-10-13	sbdc.div3@yahoo.com	shipped	224405468	15	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Jairo Chavez	Spring Branch Dental Care	20475 Highway 46 West\nSuite 310	\N	Spring Branch	TX	78070	US	(830) 438-7444	Jairo Chavez	Spring Branch Dental Care	20475 Highway 46 West\nSuite 310	\N	Spring Branch	TX	78070	US	(830) 438-7444	fedex	556346	fedex_ground	FedEx Ground	\N
463	689645	2025-10-13	lindseywood@lakewooddentaltrails.com	shipped	224432333	6	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	\N	Richard Leung	Lakewood Dental Trails	10252 W. Adams Ave.\nSte. 101	\N	Temple	TX	76502	US	(254) 206-3200	Richard Leung	Lakewood Dental Trails	10252 W. Adams Ave.\nSte. 101	\N	Temple	TX	76502	US	(254) 206-3200	fedex	556346	fedex_ground	FedEx Ground	\N
464	689655	2025-10-13	warsawstaff@orangedoordental.com	shipped	224433593	2	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	\N	Christiaan Willig	Orange Door Dental	1299 Husky Trail	\N	Warsaw	IN	46582	US	(574) 269-1200	Christiaan Willig	Orange Door Dental	1299 Husky Trail	\N	Warsaw	IN	46582	US	(574) 269-1200	fedex	556346	fedex_ground	FedEx Ground	\N
466	689675	2025-10-13	raddentalsupply@gmail.com	shipped	224447301	1	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	\N	Rose Caruso	Daws Dental	28201 W Seven Mile Rd	\N	Livonia	MI	48152	US	(248) 777-7542	Rose Caruso	Daws Dental	28201 W Seven Mile Rd	\N	Livonia	MI	48152	US	(248) 777-7542	fedex	556346	fedex_ground	FedEx Ground	\N
573	690455	2025-10-15	richardnoblet@bellsouth.net	shipped	225004504	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Charles Noblet	Noblet Family Dental	801 University Blvd\nSuite C	\N	Mobile	AL	36609	US	(251) 342-5323	Charles Noblet	Noblet Family Dental	133 Eaton Sq	\N	Mobile	AL	36608	US	2516895905	fedex	556346	fedex_ground	FedEx Ground	\N
574	690465	2025-10-15	ngrandorders@fullsmiledental.com	shipped	225004506	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Dr. Romero	Full Smile Dental N. Grand	2201 N. Grand Street	\N	Amarillo	TX	79107	US	(806) 381-1890	Full Smile Management	Billing	2201 Civic Circle	\N	Amarillo	TX	79109	US	806-381-3435	fedex	556346	fedex_ground	FedEx Ground	\N
575	690475	2025-10-15	drcaleb@cardds.com	shipped	225004508	4	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Caleb Robinson	Caleb A Robinson, DDS	541 Wabash Ave NW	\N	New Philadelphia	OH	44663	US	(614) 352-5653	Caleb Robinson	Caleb A Robinson, DDS	541 Wabash Ave NW	\N	New Philadelphia	OH	44663	US	(614) 352-5653	fedex	556346	fedex_ground	FedEx Ground	\N
643	691045	2025-10-16	rharri40@yahoo.com	shipped	\N	1	\N	X-Cart	2025-10-16 14:50:06.293462	2025-10-16 17:27:39.325556	\N	Rebecca Charpentier	Charpentier Family Dentistry	600 Rue De Onetta	\N	New Iberia	LA	70563	US	(337) 369-6587	Rebecca Charpentier	Charpentier Family Dentistry	600 Rue De Onetta	\N	New Iberia	LA	70563	US	(337) 369-6587	fedex	556346	fedex_ground	FedEx Ground	\N
460	689615	2025-10-13	diana@advancedfamilydentist.com	shipped	224402898	6	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Jeffery Gerhardt	Advanced Family Dentistry	3415 El Salido Pkwy\nSuite A	\N	Cedar Park	TX	78613	US	(512) 257-2483	Jeffery Gerhardt	Advanced Family Dentistry	3415 El Salido Pkwy\nSuite A	\N	Cedar Park	TX	78613	US	(512) 257-2483	fedex	556346	fedex_ground	FedEx Ground	\N
436	100521	2025-10-09	bills@brightdirectiondental.com	cancelled	225067355	5	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 17:58:04.892279	\N	Jennie Sahm	CENTER FOR ADVANCED DENTISTRY	8325 S EMERSON AVE STE A	\N	INDIANAPOLIS	IN	46237-8559	US	(317) 859-6768	Ruthann Witt	\N	318 West Adams Street\nSTE 400B	\N	Chicago	IL	60606	US	\N	fedex	556346	fedex_ground	FedEx Ground	\N
477	689815	2025-10-13	office@brightdentalsmiles.com	shipped	224522278	3	\N	X-Cart	2025-10-13 20:34:20	2025-10-16 17:27:39.325556	\N	Jaspreet Dhingra-Bajaj	Bright Dental Smiles	100 E.Roosevelt Road\nSuite #14	\N	Villa Park	IL	60181	US	6305010404	Jaspreet Dhingra-Bajaj	Bright Dental Smiles	224 Indian Trail Road	\N	Oakbrook	IL	60523	US	6305010404	fedex	556346	fedex_ground	FedEx Ground	\N
479	689855	2025-10-13	erin@lakefrontdds.com	shipped	224607913	1	\N	X-Cart	2025-10-14 00:14:46	2025-10-16 17:27:39.325556	\N	Erin Ransom	Hauser Phillipe Dental Partnership	31571 Canyon Estates Drive\nSuite #117	\N	Lake Elsinore	CA	92532	US	9512449495	Erin Ransom	Hauser Phillipe Dental Partnership	31571 Canyon Estates Drive\nSuite #117	\N	Lake Elsinore	CA	92532	US	9512449495	fedex	556346	fedex_ground	FedEx Ground	\N
644	691055	2025-10-16	assistants@thevillagedentalmiami.com	shipped	225326318	2	\N	X-Cart	2025-10-16 15:39:00.725004	2025-10-16 17:27:39.325556	\N	Alexandra Castillo	The Village Dental Miami	11921 S Dixie Hwy,     Suite 206	\N	Pinecrest	FL	33156	US	(305) 505-9797	Alexandra Castillo	The Village Dental Miami	11921 S Dixie Hwy,     Suite 206	\N	Pinecrest	FL	33156	US	(305) 505-9797	fedex	556346	fedex_ground	FedEx Ground	\N
645	691065	2025-10-16	ddclanghorne@gmail.com	awaiting_shipment	\N	2	\N	X-Cart	2025-10-16 17:22:04.468007	2025-10-16 17:29:44.545022	\N	Abishek Desai	Desai Dental Care	112 Corporate Drive E.\nSte 111	\N	Langhorne	PA	19047	US	(215) 860-8693	Abishek Desai	Desai Dental Care	112 Corporate Drive E.\nSte 111	\N	Langhorne	PA	19047	US	(215) 860-8693	fedex	556346	fedex_ground	FedEx Ground	\N
414	689275	2025-10-09	kristin@wilmarmanagement.com	shipped	223294533	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 14:22:53.361306	\N	Mikkah Waggamon	Residential	401 Forest Brook Drive	\N	Saint Albans	WV	25177	US	304-931-1135	Mikkah Waggamon	Residential	401 Forest Brook Drive	\N	Saint Albans	WV	25177	US	304-931-1135	fedex	556346	fedex_ground	FedEx Ground	\N
491	689985	2025-10-14	myart@webtv.net	shipped	224775606	1	\N	X-Cart	2025-10-14 16:44:35	2025-10-16 17:27:39.325556	\N	Joseph Rutland	Residential	2501 Linda Vista Ave	\N	Napa	CA	94558	US	707-938-2710	Joseph Rutland	Medical Practice	PO Box 1604	\N	Sonoma	CA	95476	US	7079382710	fedex	556346	fedex_ground	FedEx Ground	\N
544	690165	2025-10-15	familydentistry@kodiakfamily.com	shipped	224979931	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Brandon Price	Family Dentistry of Kodiak	1317 Mill Bay Road	\N	Kodiak	AK	99615	US	(907) 486-3291	Brandon Price	Family Dentistry of Kodiak	1317 Mill Bay Road	\N	Kodiak	AK	99615	US	(907) 486-3291	fedex	556346	fedex_ground	FedEx Ground	\N
557	690295	2025-10-15	info@cmdentalgroup.com	shipped	225001910	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Bridget Collins	Collins & Mingrone DDS	42 W Campbell Ave\n#204	\N	Campbell	CA	95008	US	(408) 374-6160	Bridget Collins	Collins & Mingrone DDS	42 W Campbell Ave\n#204	\N	Campbell	CA	95008	US	(408) 374-6160	fedex	556346	fedex_ground	FedEx Ground	\N
576	690485	2025-10-15	info@sprucedentalco.com	shipped	225004509	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	David Valenta	Spruce Dental	1975 Dominion Way \nSte 100	\N	Colorado Springs	CO	80918	US	(719) 388-8700	David Valenta	Spruce Dental	1975 Dominion Way \nSte 100	\N	Colorado Springs	CO	80918	US	(719) 388-8700	fedex	556346	fedex_ground	FedEx Ground	\N
577	690495	2025-10-15	drdraindmd@gmail.com	shipped	225004513	6	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Dorothy Drain	Lakeside Dental	601 Liberty Place	\N	Sicklerville	NJ	08081	US	(856) 740-1110	Dorothy Drain	Lakeside Dental	601 Liberty Place	\N	Sicklerville	NJ	08081	US	(856) 740-1110	fedex	556346	fedex_ground	FedEx Ground	\N
379	100507	2025-10-07		shipped	222760861	1	0	ShipStation Manual	2025-10-07 21:32:36	2025-10-15 05:23:36.295358	\N	Dr Ron White DDS	RON S	4189 EAST US-290	\N	DRIPPING SPRINGS	TX	78620	US	\N	Dr Ron White DDS	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
478	689825	2025-10-13	mandy@elizabethlwakimdds.com	shipped	224551458	1	\N	X-Cart	2025-10-13 21:49:07	2025-10-16 17:27:39.325556	20251013_214958_303188	Kaylee Paglialonga	Elizabeth L Wakim DDS LLC	620 North Main Street	\N	Washington	PA	15301	US	(724) 225-5070	Kaylee Paglialonga	Elizabeth L Wakim DDS LLC	620 North Main Street	\N	Washington	PA	15301	US	(724) 225-5070	fedex	556346	fedex_ground	FedEx Ground	\N
545	690175	2025-10-15	Jerichodentistry@gmail.com	shipped	224998139	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Justin Bral	Jericho Dental	366 N Broadway\nSte 302	\N	Jericho	NY	11753	US	(516) 935-0066	Justin Bral	Jericho Dental	63 Crickett Club Drive	\N	Roslyn	NY	11576	US	516-9350066	fedex	556346	fedex_ground	FedEx Ground	\N
625	690865	2025-10-15	shari@doriandoddsdds.com	shipped	225070393	1	\N	X-Cart	2025-10-15 17:54:27.796706	2025-10-16 17:27:39.325556	\N	Dorian Dodds	Dorian A. Dodds , D.D.S.	2545 Ceanothus Ave.\nste 134	\N	Chico	CA	95973	US	(530) 342-5653	Dorian Dodds	Dorian A. Dodds , D.D.S.	2545 Ceanothus Ave.\nste 134	\N	Chico	CA	95973	US	(530) 342-5653	fedex	556346	fedex_ground	FedEx Ground	\N
626	690875	2025-10-15	chehalisfamilydental@outlook.com	shipped	225088618	6	\N	X-Cart	2025-10-15 17:54:27.796706	2025-10-16 17:27:39.325556	\N	Joy Noble	Chehalis Family Dental	1299 Bishop Rd Ste B	\N	Chehalis	WA	98532	US	(360) 740-9999	Joy Noble	Chehalis Family Dental	1299 Bishop Rd Ste B	\N	Chehalis	WA	98532	US	(360) 740-9999	fedex	556346	fedex_ground	FedEx Ground	\N
395	689065	2025-10-08	jessica.emard@gmail.com	shipped	223057524	6	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Jessica Emard	West Edge Dental	88 Spring Street\nSte 100	\N	Seattle	WA	98104	US	(206) 624-8500	Jessica Emard	West Edge Dental	88 Spring Street\nSte 100	\N	Seattle	WA	98104	US	(206) 624-8500	fedex	556346	fedex_ground	FedEx Ground	\N
396	689085	2025-10-08	apollobeachdental@gmail.com	shipped	223086547	2	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Sean Gassett	Apollo Beach	433 Aplollo Beach Blvd	\N	Apollo Beach	FL	33572	US	(813) 341-0102	Sean Gassett	Apollo Beach	433 Aplollo Beach Blvd	\N	Apollo Beach	FL	33572	US	(813) 341-0102	fedex	556346	fedex_ground	FedEx Ground	\N
397	689095	2025-10-08	bestabqdentist@gmail.com	shipped	223090890	6	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Chelsea Gonzales	Academy Dental Care	6425 Holly Ave	\N	Albuquerque	NM	87113	US	505-828-2020	Chelsea Gonzalez	Academy Dental Care	8100 Wyoming  blvd\nste M4 #288	\N	Albuquerque	NM	87113	US	5058282020	fedex	556346	fedex_ground	FedEx Ground	\N
398	689105	2025-10-08	Office@portjeffdental.com	shipped	223092345	2	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Rebecca Camilleri	Port Jefferson Dental Group	602 Main Street	\N	Port Jefferson	NY	11780	US	(631) 473-1511	Rebecca Camilleri	Port Jefferson Dental Group	602 Main Street	\N	Port Jefferson	NY	11780	US	(631) 473-1511	fedex	556346	fedex_ground	FedEx Ground	\N
399	689115	2025-10-08	isabella@balledds.com	shipped	223353330	3	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Peter Balle	Balle and Associates	2801 West Charleston Blvd\nSuite 100	\N	Las Vegas	NV	89102	US	(702) 877-6608	Peter Balle	Balle and Associates	2801 West Charleston Blvd\nSuite 100	\N	Las Vegas	NV	89102	US	(702) 877-6608	fedex	556346	fedex_ground	FedEx Ground	\N
400	689125	2025-10-08	famdentpa@yahoo.com	shipped	223101636	6	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Anthony Polit	Polit & Costello Dentistry	457 N. Main Street\nSuite 100	\N	Pittston	PA	18640	US	(570) 655-7645	Anthony Polit	Polit & Costello Dentistry	457 N. Main Street\nSuite 100	\N	Pittston	PA	18640	US	(570) 655-7645	fedex	556346	fedex_ground	FedEx Ground	\N
401	689135	2025-10-08	heather.idealdental@gmail.com	shipped	223352903	3	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Alex Flora	Ideal Dental	1025 3rd Ave	\N	Woodruff	WI	54401	US	7153562777	Alexander Flora	Ideal Dental	PO Box 680	\N	Woodruff	WI	54568	US	7153562777	fedex	556346	fedex_ground	FedEx Ground	\N
422	100465	2025-08-26		shipped	211474875	15	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Laura Rabbitts	WOODBOROUGH HOUSE DENTAL PRACTICE	21 Reading Road	\N	Reading	West Berkshire	RG8 7LR	GB	\N	Laura Rabbitts	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_international_economy	Fedex International Economy	\N
413	689265	2025-10-09	payables@humphriesdental.com	shipped	223293231	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:38:33.956809	\N	James Humphries Jr	Humphries Dental	2711 Fourth Street	\N	Bay City	TX	77414	US	(979) 245-6541	James Humphries Jr	Humphries Dental	2711 Fourth Street	\N	Bay City	TX	77414	US	(979) 245-6541	fedex	556346	fedex_ground	FedEx Ground	\N
579	690515	2025-10-15	bridget@myprosmile.com	shipped	225004518	4	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Michael Freimuth	ProSmile	10135 W. 38th Ave	\N	Wheat Ridge	CO	80033	US	(303) 431-5830	Michael Freimuth	ProSmile	10135 W. 38th Ave	\N	Wheat Ridge	CO	80033	US	(303) 431-5830	fedex	556346	fedex_ground	FedEx Ground	\N
580	690525	2025-10-15	info@zanedentalmn.com	shipped	225005520	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Quang Nguyen	Zane Dental	7340 Zane Ave N	\N	Minneapolis	MN	55443	US	(763) 561-1200	Quang Nguyen	Zane Dental	7340 Zane Ave N	\N	Minneapolis	MN	55443	US	(763) 561-1200	fedex	556346	fedex_ground	FedEx Ground	\N
581	690535	2025-10-15	info@elitedentalllc.com	shipped	225005523	3	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Mimi Hoang	Elite Dental LLC	1525 Livingston Ave\nSte 2	\N	West St Paul	MN	55118	US	7635611200	Mimi Hoang	Elite Dental LLC	1525 Livingston Ave\nSte 2	\N	West St Paul	MN	55118	US	7635611200	fedex	556346	fedex_ground	FedEx Ground	\N
618	100532	2025-10-13	\N	shipped	225073075	0	\N	X-Cart	2025-10-15 17:16:54.695924	2025-10-15 17:58:04.892279	20251015_175428_141954	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
558	690305	2025-10-15	jessica@healthyteethdentalcare.com	shipped	225001912	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Jessica Frantom	Healthy Teeth Dental Care	417 SW Sedgwick Rd	\N	Port Orchard	WA	98366	US	(360) 329-4657	Jessica Frantom	Healthy Teeth Dental Care	417 SW Sedgwick Rd	\N	Port Orchard	WA	98366	US	(360) 329-4657	fedex	556346	fedex_ground	FedEx Ground	\N
559	690315	2025-10-15	officemgr@infinitydentallv.com	shipped	225001916	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Brittany Cain	Infinity Dental	8940 w. Tropicana Ave	\N	Las Vegas	NV	89147	US	(702) 248-4448	Brittany Cain	Infinity Dental	8940 w. Tropicana Ave	\N	Las Vegas	NV	89147	US	(702) 248-4448	fedex	556346	fedex_ground	FedEx Ground	\N
578	690505	2025-10-15	hygiene@songdental.com	shipped	225004515	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Brian Song	Song Dental	6717 Kingery Hwy	\N	Willowbrook	IL	60527	US	(630) 655-8781	Brian Song	Song Dental	6717 Kingery Hwy	\N	Willowbrook	IL	60527	US	(630) 655-8781	fedex	556346	fedex_ground	FedEx Ground	\N
423	100508	2025-10-08	alivia@oracareproducts.com	shipped	223022623	3	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Elaine Halley	Cherrybank Dental Spa	168 Glasgow Road	\N	Perth	Perth & Kinross	PH2 0LY	GB	8552556722	Elaine Halley	\N	\N	\N	\N	\N	\N	\N	8552556722	fedex	556346	fedex_international_economy	Fedex International Economy	\N
424	100509	2025-10-08	info@eastparkdental.com	shipped	223115617	6	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Karl Weaver	EASTPARK DENTAL	5100 EASTPARK BLVD STE 110	\N	MADISON	WI	53718-2149	US	6082228232	Karl Weaver	\N	\N	\N	\N	\N	\N	\N	6082228232	fedex	556346	fedex_ground	FedEx Ground	\N
425	100510	2025-10-08		shipped	223133439	3	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	OVERLAND PARK MODERN DENTISTRY	OVERLAND PARK MODERN DENTISTRY	13316 METCALF AVE	\N	OVERLAND PARK	KS	66213-2804	US	\N	OVERLAND PARK MODERN DENTISTRY	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_2day	FedEx 2Day	\N
426	100511	2025-10-08		shipped	223135150	1	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	OVERLAND PARK MODERN DENTISTRY	OVERLAND PARK MODERN DENTISTRY	13316 METCALF AVE	\N	OVERLAND PARK	KS	66213-2804	US	\N	OVERLAND PARK MODERN DENTISTRY	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
427	100512	2025-10-09		shipped	223286454	1	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Cloudland Dental	\N	4972 HIGHWAY 58 STE 114	\N	CHATTANOOGA	TN	37416-1868	US	\N	Cloudland Dental	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
564	690365	2025-10-15	unionpark@prodent.email	shipped	225001932	6	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	John Myers	Professional Dental Union Park	7455 S Union Park\nSuite C	\N	Midvale	UT	84047	US	(801) 262-7770	BILLING BILLING	BILLING	1172 West	\N	Lindon	UT	84042	US	801-636-0631	fedex	556346	fedex_ground	FedEx Ground	\N
605	690785	2025-10-15	jaressfamilydentistry@gmail.com	shipped	\N	2	\N	X-Cart	2025-10-15 16:56:57.594205	2025-10-16 17:27:39.325556	\N	Amber Jaress	Jaress Family Dentistry	1934 W LINCOLN AVE	\N	GOSHEN	IN	46526	US	(574) 533-0722	Amber Jaress	Jaress Family Dentistry	1934 W LINCOLN AVE	\N	GOSHEN	IN	46526	US	(574) 533-0722	fedex	556346	fedex_ground	FedEx Ground	\N
606	690795	2025-10-15	JLCHENGDMD@gmail.com	shipped	\N	1	\N	X-Cart	2025-10-15 16:56:57.594205	2025-10-16 17:27:39.325556	\N	James Cheng	Main Street Dental of Loganville	238 Main Street	\N	Loganville	GA	30052	US	(770) 466-2231	James Cheng	Main Street Dental of Loganville	238 Main Street	\N	Loganville	GA	30052	US	(770) 466-2231	fedex	556346	fedex_ground	FedEx Ground	\N
607	690805	2025-10-15	jorgorderdesk@gmail.com	shipped	\N	3	\N	X-Cart	2025-10-15 16:56:57.594205	2025-10-16 17:27:39.325556	\N	Gretchen Jorg	Jorg Family Dentistry	6319 24th Ave NorthWest	\N	Seattle	WA	98107	US	(206) 784-7171	Gretchen Jorg	Jorg Family Dentistry	6319 24th Ave NorthWest	\N	Seattle	WA	98107	US	(206) 784-7171	fedex	556346	fedex_ground	FedEx Ground	\N
446	100524	2025-10-10	noemail@oracare.com	cancelled	225067382	1	0	ShipStation Manual	2025-10-10 20:18:36	2025-10-15 17:58:04.892279	\N	Kaye Dentistry	\N	455 CENTRAL PARK AVE STE 315	\N	SCARSDALE	NY	10583-1034	US	\N	Kaye Dentistry	\N	455 CENTRAL PARK AVE STE 315	\N	SCARSDALE	NY	10583-1034	US	\N	fedex	556346	fedex_ground	FedEx Ground	\N
560	690325	2025-10-15	savannahsmilesdentalschertz@gmail.com	shipped	225001919	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Melissa Ruiz	Savannah Smiles Dental	1205 Savannh Drive	\N	Schertz	TX	78154	US	(210) 659-9001	Melissa Ruiz	Savannah Smiles Dental	1205 Savannh Drive	\N	Schertz	TX	78154	US	(210) 659-9001	fedex	556346	fedex_ground	FedEx Ground	\N
561	690335	2025-10-15	dentistsuperdad@gmail.com	shipped	225001922	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Nahvid Jafarnejad	Cameron Park Family Dentistry	4058 Flying C Rd\nSuite 9	\N	Cameron Park	CA	95682	US	9165990851	Nahvid Jafarnejad	Cameron Park Family Dentistry	438 Listowe Dr	\N	Folsom	CA	95630	US	9165990851	fedex	556346	fedex_ground	FedEx Ground	\N
562	690345	2025-10-15	westlakedentalco@gmail.com	shipped	225001924	3	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Stephanie Canar	West Lake Dental	650 West Eisenhower Blvd\nSte 200	\N	Loveland	CO	80537	US	(970) 669-1444	Stephanie Canar	West Lake Dental	650 West Eisenhower Blvd\nSte 200	\N	Loveland	CO	80537	US	(970) 669-1444	fedex	556346	fedex_ground	FedEx Ground	\N
563	690355	2025-10-15	gmd77380@gmail.com	shipped	225001930	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Donna Goodie	Grogans Mill Dental	25210 Grogans Mill Rd	\N	The Woodlands	TX	77380	US	(281) 298-5225	Donna Goodie	Grogans Mill Dental	25210 Grogans Mill Rd	\N	The Woodlands	TX	77380	US	(281) 298-5225	fedex	556346	fedex_ground	FedEx Ground	\N
473	100526	2025-10-13	staff@elitedentistrytn.com	cancelled	225067406	1	0	ShipStation Manual	2025-10-13 19:52:04	2025-10-15 17:58:04.892279	\N	Dr. Eric Schuh	ELITE DENTISTRY	615 COMMONS DR	\N	GALLATIN	TN	37066-6318	US	6152306611	Dr. Eric Schuh	\N	\N	\N	\N	\N	\N	\N	6152306611	fedex	556346	fedex_ground	FedEx Ground	\N
582	690545	2025-10-15	atw@mfdentistry.biz	shipped	225005526	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Tammy Eichelberger	MODERN FAMILY DENTISTRY	3195 Cold Springs Road	\N	HUNTINGDON	PA	16652	US	(814) 643-7300	Tammy Eichelberger	MODERN FAMILY DENTISTRY	3195 Cold Springs Road	\N	HUNTINGDON	PA	16652	US	(814) 643-7300	fedex	556346	fedex_ground	FedEx Ground	\N
583	690555	2025-10-15	marc_nevins@hms.harvard.edu	shipped	225005528	10	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Marc Nevins	Nevins Dental Center	3 Center Plaza\nste 310	\N	Boston	MA	02108	US	(617) 720-0285	Marc Nevins	Nevins Dental Center	3 Center Plaza\nste 310	\N	Boston	MA	02108	US	(617) 720-0285	fedex	556346	fedex_ground	FedEx Ground	\N
598	690705	2025-10-15	maxrodefferdmd@gmail.com	shipped	225006655	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Max Rodeffer	Max A. Rodeffer, DMD	911 Broadway Street	\N	Hamilton	IL	62341	US	(217) 847-3900	Max Rodeffer	Max A. Rodeffer, DMD	911 Broadway Street	\N	Hamilton	IL	62341	US	(217) 847-3900	fedex	556346	fedex_ground	FedEx Ground	\N
603	690765	2025-10-15	info@langworthydental.com	shipped	\N	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	William May	Langworthy Dental Group PC	989 Langworthy St	\N	Dubuque	IA	52001	US	(563) 583-2681	William May	Langworthy Dental Group PC	989 Langworthy St	\N	Dubuque	IA	52001	US	(563) 583-2681	fedex	556346	fedex_ground	FedEx Ground	\N
604	690775	2025-10-15	admin@sicklervillesmiles.com	shipped	\N	6	\N	X-Cart	2025-10-15 14:50:25.126422	2025-10-16 17:27:39.325556	\N	Robert Santorsa	Sicklerville Smiles	423 Sicklerville Rd	\N	Sicklerville	NJ	08081	US	(856) 728-9200	BILLING Billing	Sicklerville Smiles	921 Woodby Court	\N	Williamstown	NJ	08094	US	856-728-9200	fedex	556346	fedex_ground	FedEx Ground	\N
601	690735	2025-10-15	admin@drjaynedentistry.com	shipped	\N	3	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Jayne Hoffman	Dr. Jayne Dentistry-TRUBLU	1250 Scott Blvd	\N	Santa Clara	CA	95050	US	(669) 201-0334	Jayne Hoffman	Dr. Jayne Dentistry-TRUBLU	1250 Scott Blvd	\N	Santa Clara	CA	95050	US	(669) 201-0334	fedex	556346	fedex_ground	FedEx Ground	\N
602	690745	2025-10-15	Cockrelldental@yahoo.com	shipped	\N	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Kevin Cockrell	Cockrell Dental Office	1040 Hillcrest Rd	\N	Mobile	AL	36695	US	(251) 639-0110	Kevin Cockrell	Cockrell Dental Office	1040 Hillcrest Rd	\N	Mobile	AL	36695	US	(251) 639-0110	fedex	556346	fedex_ground	FedEx Ground	\N
609	690835	2025-10-15	toothdoctor35@yahoo.com	shipped	\N	1	\N	X-Cart	2025-10-15 16:56:57.594205	2025-10-16 17:27:39.325556	\N	David Powell	All Care Dentistry	6065 South Fashion Blvd #275	\N	Murray	UT	84107	US	(801) 266-1414	David Powell	All Care Dentistry	6065 South Fashion Blvd #275	\N	Murray	UT	84107	US	(801) 266-1414	fedex	556346	fedex_ground	FedEx Ground	\N
610	690845	2025-10-15	officemanager@kennestonedentalcare.com	shipped	\N	6	\N	X-Cart	2025-10-15 16:56:57.594205	2025-10-16 17:27:39.325556	\N	Angela Ojibway	Dental Care Center at Kennestone	129 Marble Mill Rd NW	\N	Marietta	GA	30060	US	(770) 424-4565	Angela Ojibway	Dental Care Center at Kennestone	129 Marble Mill Rd NW	\N	Marietta	GA	30060	US	(770) 424-4565	fedex	556346	fedex_ground	FedEx Ground	\N
611	690855	2025-10-15	info@paducahdentist.com	shipped	\N	1	\N	X-Cart	2025-10-15 16:56:57.594205	2025-10-16 17:27:39.325556	\N	Holly Turner	Cunningham Dental	2465 New Holt Road	\N	Paducah	KY	42001	US	(270) 366-0735	Holly Turner	Cunningham Dental	2465 New Holt Road	\N	Paducah	KY	42001	US	(270) 366-0735	fedex	556346	fedex_ground	FedEx Ground	\N
408	689205	2025-10-09	montrealdental@yahoo.com	shipped	223258235	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:38:33.956809	\N	Hiren Patel	Montreal Dental	1462 Montreal Road, Suite 211	\N	Tucker	GA	30084	US	(770) 938-1848	Hiren Patel	Montreal Dental	1462 Montreal Road, Suite 211	\N	Tucker	GA	30084	US	(770) 938-1848	fedex	556346	fedex_ground	FedEx Ground	\N
409	689225	2025-10-09	kdoker18@gmail.com	shipped	223274020	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:38:33.956809	\N	Kricket Doker	Guffee Dental Associates	26 Holly Creek Drive	\N	Anderson	SC	29621	US	(864) 226-1752	Kricket Doker	Guffee Dental Associates	26 Holly Creek Drive	\N	Anderson	SC	29621	US	(864) 226-1752	fedex	556346	fedex_ground	FedEx Ground	\N
410	689235	2025-10-09	info@moderndentalroswell.com	shipped	223274958	15	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:38:33.956809	\N	Ashish KAKADIA	Modern Dentistry	1755 WOODSTOCK RD STE 100\nSUITE 100	\N	ROSWELL	GA	30075	US	(770) 993-6893	Ashish KAKADIA	Modern Dentistry	1755 WOODSTOCK RD STE 100\nSUITE 100	\N	ROSWELL	GA	30075	US	(770) 993-6893	fedex	556346	fedex_ground	FedEx Ground	\N
411	689245	2025-10-09	supplies@chasehalldmd.com	shipped	223276005	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:38:33.956809	\N	Jonathon Hall	Dr. Jonathan Chase Hall DMD	3400 A Old Milton Parkway\nSuite 540	\N	Alpharetta	GA	30005	US	(770) 751-0650	Jonathon Hall	Dr. Jonathan Chase Hall DMD	3400 A Old Milton Parkway\nSuite 540	\N	Alpharetta	GA	30005	US	(770) 751-0650	fedex	556346	fedex_ground	FedEx Ground	\N
412	689255	2025-10-09	cliniccoordinator@thewoodlandsdental.com	shipped	223290272	6	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:38:33.956809	\N	Clinic Coordinator	Woodlands Dental Group	1001 Medical Plaza Dr.\nSuite 300	\N	The Woodlands	TX	77380	US	(281) 367-3900	Clinic Coordinator	Woodlands Dental Group	1001 Medical Plaza Dr.\nSuite 300	\N	The Woodlands	TX	77380	US	(281) 367-3900	fedex	556346	fedex_ground	FedEx Ground	\N
599	690715	2025-10-15	payables@humphriesdental.com	shipped	\N	6	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	James Humphries Jr	Humphries Dental	2711 Fourth Street	\N	Bay City	TX	77414	US	(979) 245-6541	James Humphries Jr	Humphries Dental	2711 Fourth Street	\N	Bay City	TX	77414	US	(979) 245-6541	fedex	556346	fedex_ground	FedEx Ground	\N
600	690725	2025-10-15	zavodnydental2950@gmail.com	shipped	\N	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Robert Zavodny	Zavodny Dental	2950 W. Market St. Ste N-O	\N	Fairlawn	OH	44333	US	(330) 836-9511	Robert Zavodny	Zavodny Dental	2950 W. Market St. Ste N-O	\N	Fairlawn	OH	44333	US	(330) 836-9511	fedex	556346	fedex_ground	FedEx Ground	\N
415	689285	2025-10-09	drwilliam@stewartfamilydentistrysc.com	shipped	223295533	3	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 14:28:19.497687	\N	William Stewart	Stewart Family Dentistry	1327 Drayton Road	\N	Spartanburg	SC	29307	US	(864) 583-0793	William Stewart	Stewart Family Dentistry	1327 Drayton Road	\N	Spartanburg	SC	29307	US	(864) 583-0793	fedex	556346	fedex_ground	FedEx Ground	\N
483	689905	2025-10-14	brittany@smilecabarrus.com	shipped	224708330	2	\N	X-Cart	2025-10-14 13:03:20	2025-10-16 17:27:39.325556	\N	Reid Chaney	Smile Cabarrus	5000 Hwy 49 S	\N	Harrisburg	NC	28075	US	(704) 455-3333	Reid Chaney	Smile Cabarrus	220 Branchview Dr SE	\N	Concord	NC	28025	US	7044553333	fedex	556346	fedex_ground	FedEx Ground	\N
484	689915	2025-10-14	MLB19780@outlook.com	shipped	224723211	6	\N	X-Cart	2025-10-14 14:03:39	2025-10-16 17:27:39.325556	\N	Micki Bates	East Limestone Family Dental	15059 East Limestone Road	\N	Harvest	AL	35749	US	(256) 216-8525	Micki Bates	East Limestone Family Dental	15059 East Limestone Road	\N	Harvest	AL	35749	US	(256) 216-8525	fedex	556346	fedex_ground	FedEx Ground	\N
485	689925	2025-10-14	hamburg.expressions@yahoo.com	shipped	224734472	6	\N	X-Cart	2025-10-14 14:48:58	2025-10-16 17:27:39.325556	\N	Jenny Miller	Hamburg Expressions	3292 Eagle View Lane Suite 110	\N	Lexington	KY	40509	US	(859) 543-9000	Jenny Miller	Hamburg Expressions	3292 Eagle View Lane Suite 110	\N	Lexington	KY	40509	US	(859) 543-9000	fedex	556346	fedex_ground	FedEx Ground	\N
486	689935	2025-10-14	woods@alamocitysmiles.com	shipped	224736413	6	\N	X-Cart	2025-10-14 14:53:59	2025-10-16 17:27:39.325556	\N	Kristi Woowine	Alamo City Smiles	7272 Wurzbach Rd\nSte 404	\N	San Antonio	TX	78240	US	(210) 615-1545	Kristi Woowine	Alamo City Smiles	7272 Wurzbach Rd\nSte 404	\N	San Antonio	TX	78240	US	(210) 615-1545	fedex	556346	fedex_ground	FedEx Ground	\N
487	689945	2025-10-14	winnsmilesfrontoffice@gmail.com	shipped	224738760	6	\N	X-Cart	2025-10-14 15:04:02	2025-10-16 17:27:39.325556	\N	Bradley Winn	Winn Smiles	148 Stuart Crossing NW	\N	Cleveland	TN	37312	US	4234726482	Bradley Winn	Winn Smiles	148 Stuart Crossing NW	\N	Cleveland	TN	37312	US	4234726482	fedex	556346	fedex_ground	FedEx Ground	\N
488	689955	2025-10-14	deanna@atlasdentistry.com	shipped	224760476	15	\N	X-Cart	2025-10-14 15:54:19	2025-10-16 17:27:39.325556	\N	Deanna Brown	Reflection Dentistry	1502 Bishop Rd SW	\N	Tumwater	WA	98512	US	(253) 380-0370	Deanna Brown	Reflection Dentistry	1502 Bishop Rd SW	\N	Tumwater	WA	98512	US	(253) 380-0370	fedex	556346	fedex_ground	FedEx Ground	\N
489	689965	2025-10-14	info@isabellaavenuedentistry.com	shipped	224760479	1	\N	X-Cart	2025-10-14 15:54:19	2025-10-16 17:27:39.325556	\N	Leslie Strommer	Isabella Avenue Dentistry	1012 Isabella Ave	\N	Coronado	CA	92118	US	(619) 993-5078	Leslie Stromer	Isabella Ave	7800 east union ave\nSte930	\N	Denver	CO	80237	US	6194350147	fedex	556346	fedex_ground	FedEx Ground	\N
481	689885	2025-10-14	Cjpaulsondds@gmail.com	shipped	224692567	1	\N	X-Cart	2025-10-14 10:47:38	2025-10-16 17:27:39.325556	\N	Chris Paulson	Arbor Dental Associates	44170 w. 12 mile\nSte.200	\N	Novi	MI	48377	US	(248) 553-9393	Chris Paulson	Arbor Dental Associates	44170 w. 12 mile\nSte.200	\N	Novi	MI	48377	US	(248) 553-9393	fedex	556346	fedex_ground	FedEx Ground	\N
482	689895	2025-10-14	nancy@seaportdentistry.com	shipped	224704339	40	\N	X-Cart	2025-10-14 12:38:11	2025-10-16 17:27:39.325556	\N	Nancy English	Seaport Family Dentistry	2 Westwoods Dr	\N	Liberty	MO	64068	US	(816) 781-1430	Nancy English	Seaport Family Dentistry	2 Westwoods Dr	\N	Liberty	MO	64068	US	(816) 781-1430	fedex	556346	fedex_ground	FedEx Ground	\N
584	690565	2025-10-15	drsteve@muhadental.com	shipped	225005533	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Steven Muha	Muha Dental	1225 Graham Ave	\N	Windber	PA	15963	US	(814) 467-7498	Steven Muha	Muha Dental	1225 Graham Ave	\N	Windber	PA	15963	US	(814) 467-7498	fedex	556346	fedex_ground	FedEx Ground	\N
585	690575	2025-10-15	dawson@smilescience.com	shipped	225005536	5	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Richard Dawson	Smile Science Dental Spa	20118 n 67th Ave\nSte 308	\N	Glendale	AZ	85308	US	(480) 530-3663	Richard Dawson	Smile Scienece Dental Spa	20118 n 67th Ave	\N	Glendale	AZ	85308	US	4805303663	fedex	556346	fedex_ground	FedEx Ground	\N
586	690585	2025-10-15	mrp240@nyu.edu	shipped	225005538	5	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Mitul Patel	Hello Family Dental	2905 PEACHTREE PARKWAY	\N	SUWANEE	GA	30024	US	(678) 230-1104	Mitul Patel	Hello Family Dental	2905 PEACHTREE PARKWAY	\N	SUWANEE	GA	30024	US	(678) 230-1104	fedex	556346	fedex_ground	FedEx Ground	\N
546	690185	2025-10-15	lauraday@premdent.com	shipped	224998148	3	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Steve Kail	Premier Dental	7019 Highway 412 South	\N	Bell	TN	38006	US	(731) 663-9999	Steve Kail	Premier Dental	7019 Highway 412 South	\N	Bell	TN	38006	US	(731) 663-9999	fedex	556346	fedex_ground	FedEx Ground	\N
547	690195	2025-10-15	tulanefamilydentistry@gmail.com	shipped	224999416	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	William Shelton	Tulane Family Dentistry-TB	1600 St Charles Ave\nSte 201	\N	New orleans	LA	70130	US	504-304-9929	William Shelton	Tulane Family Dentistry-TB	1600 St Charles Ave\nSte 201	\N	New orleans	LA	70130	US	504-304-9929	fedex	556346	fedex_ground	FedEx Ground	\N
549	690215	2025-10-15	info@zegerdental.com	shipped	224999421	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Kirk Zeger	Kirk M Zeger, DMD	110 East Franklin Street	\N	Greencastle	PA	17225	US	(717) 597-2507	Kirk Zeger, DMD	Kirk M Zeger, DMD	429 South Edwards Ave	\N	chambersburg	PA	17202	US	7175972507	fedex	556346	fedex_ground	FedEx Ground	\N
550	690225	2025-10-15	carlsbaddr@outlook.com	shipped	224999428	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Paul Rappaport	Rappaport Family Dentistry	2963 Madison St	\N	Carlsbad	CA	92008	US	(760) 730-0400	Paul Rappaport	Rappaport Family Dentistry	2963 Madison St	\N	Carlsbad	CA	92008	US	(760) 730-0400	fedex	556346	fedex_ground	FedEx Ground	\N
551	690235	2025-10-15	contact@dentalvisions.com	shipped	224999430	3	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	James Denton	Dental Visions	116 W Renfro St	\N	Burleson	TX	76028	US	(817) 295-7116	James Denton	Dental Visions	116 W Renfro St	\N	Burleson	TX	76028	US	(817) 295-7116	fedex	556346	fedex_ground	FedEx Ground	\N
552	690245	2025-10-15	info@moderndentalroswell.com	shipped	224999433	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Ashish KAKADIA	Modern Dentistry	1755 WOODSTOCK RD STE 100\nSUITE 100	\N	ROSWELL	GA	30075	US	(770) 993-6893	Ashish KAKADIA	Modern Dentistry	1755 WOODSTOCK RD STE 100\nSUITE 100	\N	ROSWELL	GA	30075	US	(770) 993-6893	fedex	556346	fedex_ground	FedEx Ground	\N
553	690255	2025-10-15	Smiles@fullheartdentistry.com	shipped	224999435	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Sarah Smith	Full Heart Dentistry	632 Winton Rd N.	\N	Rochester	NY	14609	US	(585) 342-7902	Sarah Smith	Full Heart Dentistry	PO Box 10797	\N	Rochester	NY	14610	US	5853427902	fedex	556346	fedex_ground	FedEx Ground	\N
554	690265	2025-10-15	office@bondsranchfamilydentistry.com	shipped	224999439	2	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Rhiannon Presley	Bonds Ranch Family Dentistry	750 W Bonds Ranch Rd\nSuite 100	\N	Ft Worth	TX	76131	US	(817) 242-5564	Rhiannon Presley	Bonds Ranch Family Dentistry	750 W Bonds Ranch Rd\nSuite 100	\N	Ft Worth	TX	76131	US	(817) 242-5564	fedex	556346	fedex_ground	FedEx Ground	\N
555	690275	2025-10-15	winchesterfamilydentistrytn@gmail.com	shipped	224999441	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Garrett Orr	Winchester Family Dentistry	1741 Bypass Rd, Winchester,	\N	Winchester	TN	37330	US	(931) 967-4143	Garrett Orr	Winchester Family Dentistry	1741 Bypass Rd, Winchester,	\N	Winchester	TN	37330	US	(931) 967-4143	fedex	556346	fedex_ground	FedEx Ground	\N
480	689865	2025-10-13	Pfangmann@dentalstudiomidland.com	shipped	224610323	1	\N	X-Cart	2025-10-14 00:24:49	2025-10-16 17:27:39.325556	\N	Patricia Fangmann	Caldwell Dental	6 Desta Dr Suite 2700	\N	Midland	TX	79705	US	(432) 694-1659	Patricia Fangmann	Caldwell Dental	6 Desta Dr Suite 2700	\N	Midland	TX	79705	US	(432) 694-1659	fedex	556346	fedex_ground	FedEx Ground	\N
589	690615	2025-10-15	VelazquezBackOffice@gmail.com	shipped	225005543	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Luis Velazquez	Velazquez Dental Office	8977 FOOTHILL BLVD\nF	\N	RCH CUCAMONGA	CA	91730	US	(909) 527-3242	Luis Velazquez	Velazquez Dental Office	8977 FOOTHILL BLVD\nF	\N	RCH CUCAMONGA	CA	91730	US	(909) 527-3242	fedex	556346	fedex_ground	FedEx Ground	\N
110	682585	2025-09-10	info@cliniquedac.com	shipped	215890264	2	0	ShipStation Manual	2025-10-02 21:38:25	2025-10-15 05:23:36.295358	\N	Dac Nguyen	Clinique Dentaire Dac	550-4141 Sherbrooke St W	\N	Westmount	QC	H3Z 1B8	CA	(514) 934-0748	Dac Nguyen	Clinique Dentaire Dac	4141 Sherbrooke St W\nSte 550	\N	Westmount	QC	H3Z-1B8	CA	(514) 934-0748	fedex	556346	fedex_international_priority_express	Fedex International Priority Express	\N
286	683035	2025-09-12	prosupplies@heartland.com	shipped	216954484	2	0	ShipStation Manual	2025-10-06 15:14:19	2025-10-15 05:23:36.295358	\N	Dental Care of Naples Lake	HEARTLAND DENTAL	8615 COLLIER BLVD	\N	NAPLES	FL	34114-3550	US	2175405100	Heartland Dental	Heartland Dental	1200 Network Centre Dr	\N	Effingham	IL	62401	US	2175405100	fedex	556346	fedex_ground	FedEx Ground	\N
142	684985	2025-09-22	info@toothdoctorhawaiikai.com	shipped	219071466	1	0	ShipStation Manual	2025-10-02 21:38:26	2025-10-15 05:23:36.295358	\N	Ha Kim	TOOTH DOCTOR	377 KEAHOLE ST STE E211A	\N	HONOLULU	HI	96825-3413	US	(808) 393-2020	Ha Kim	TOOTH DOCTOR	377 KEAHOLE ST STE E211A	\N	HONOLULU	HI	96825-3413	US	8083932020	fedex	556346	fedex_2day	FedEx 2Day	\N
282	686065	2025-09-24	bodiestaff@drjackbodie.com	shipped	219534433	2	0	ShipStation Manual	2025-10-03 17:14:14	2025-10-15 05:23:36.295358	\N	Jack  Bodie	DR. JACK BODIE DENTISTRY	800 E CAMPBELL RD STE 180	\N	RICHARDSON	TX	75081-1862	US	(972) 235-4767	Jack  Bodie	Dr. Jack Bodie Dentistry	800 East Campbell \n#180	\N	Richardson	TX	75081	US	(972) 235-4767	fedex	556346	fedex_ground	FedEx Ground	\N
18	686725	2025-09-29	info@peakcitydentistry.com	shipped	220646610	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Christopher Tikvart	Peak City Family Dentistry	200 W Chatham St	\N	Apex	NC	27502	US	9193628797	Christopher Tikvart	Peak City Family Dentistry	200 W Chatham St	\N	Apex	NC	27502	US	9193628797	fedex	556346	fedex_ground	FedEx Ground	\N
30	686855	2025-09-30	drblsilver@gmail.com	shipped	220854693	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Bruce Silver	Silver Dental Associates	1816 MT. Holly Road\nSte 101	\N	Burlington	NJ	08016	US	(609) 387-1844	Bruce Silver	Silver Dental Associates	1816 MT. Holly Road\nSte 101	\N	Burlington	NJ	08016	US	(609) 387-1844	ups_walleted	556331	ups_ground	Ups Ground	\N
31	686865	2025-09-30	drblsilver@gmail.com	shipped	220862555	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Bruce Silver	Silver Dental Associates	1816 MT. Holly Road\nSte 101	\N	Burlington	NJ	08016	US	(609) 387-1844	Bruce Silver	Silver Dental Associates	1816 MT. Holly Road\nSte 101	\N	Burlington	NJ	08016	US	(609) 387-1844	ups_walleted	556331	ups_ground	Ups Ground	\N
35	686915	2025-09-30	drjameschoy@yahoo.com	shipped	220944277	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	James Choy	Aloha Dental Associates - Dr. James Choy	970 N Kalaheo Ave\nSte A101	\N	KAILUA	HI	96734	US	8082542339	James Choy	Aloha Dental Associates - Dr. James Choy	970 N Kalaheo Ave\nSte A101	\N	KAILUA	HI	96734	US	8082542339	fedex	556346	fedex_2day	FedEx 2Day	\N
36	686925	2025-09-30	drp@cherishedsmilesdentistry.com	shipped	220948352	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Patricia Homer	Cherished Smiles Family Dentistry	7454 Hannover Pkwy S	\N	Stockbridge	GA	30281	US	(678) 289-0024	Patricia Homer	Cherished Smiles Family Dentistry	7454 Hannover Pkwy S	\N	Stockbridge	GA	30281	US	(678) 289-0024	fedex	556346	fedex_ground	FedEx Ground	\N
37	686945	2025-09-30	westownpkwy@cordentalgroup.com	shipped	221230670	2	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Gregory Ceraso	TC Dental Partners	4201 Westown Pkwy\nSuite 118, Highland Building	\N	West Des Moines	IA	50266	US	(515) 223-1213	Gregory Ceraso	TC Dental Partners	4201 Westown Pkwy\nSuite 118, Highland Building	\N	West Des Moines	IA	50266	US	(515) 223-1213	fedex	556346	fedex_ground	FedEx Ground	\N
38	686955	2025-09-30	lab@lakeviewdentistryofcharlevoix.com	shipped	220954357	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Melissa Makowski	Lakeview Dentistry of Charlevoix	411 Bridge st.	\N	Charlevoix	MI	49720	US	(231) 547-4347	Melissa Makowski	Lakeview Dentistry of Charlevoix	PO Box 325	\N	Eastport	MI	49627	US	(231) 547-4347	fedex	556346	fedex_ground	FedEx Ground	\N
39	686965	2025-09-30	assistants@thevillagedentalmiami.com	shipped	220961430	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Alexandra Castillo	The Village Dental Miami	11921 S Dixie Hwy,     Suite 206	\N	Pinecrest	FL	33156	US	(305) 505-9797	Alexandra Castillo	The Village Dental Miami	11921 S Dixie Hwy,     Suite 206	\N	Pinecrest	FL	33156	US	(305) 505-9797	fedex	556346	fedex_ground	FedEx Ground	\N
40	686975	2025-09-30	livingstondental211@gmail.com	shipped	220959961	4	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Michael Lee	Livingston Dental Arts	22 Old Short Hills Rd\nSuite 211	\N	Livingston	NJ	07039	US	9739947200	Michael Lee	Livingston Dental Arts	22 Old Short Hills Rd\nSuite 211	\N	Livingston	NJ	07039	US	9739947200	fedex	556346	fedex_ground	FedEx Ground	\N
41	686985	2025-09-30	business@erskinefamilydentistry.com	shipped	220964829	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Lori Risser	Erskine Family Dentistry	734 East Ireland Road	\N	South Bend	IN	46614	US	(574) 299-9300	Lori Risser	Erskine Family Dentistry	734 East Ireland Road	\N	South Bend	IN	46614	US	(574) 299-9300	fedex	556346	fedex_ground	FedEx Ground	\N
590	690625	2025-10-15	halliemccallum@premdent.com	shipped	225006627	5	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Christopher Arnold	Premier Dental Center	80 Exerter Road	\N	Jackson	TN	38305	US	(731) 300-3000	Christopher Arnold	Premier Dental Center	7019 HWY 412 S	\N	Bells	TN	38006	US	731-300-3000	fedex	556346	fedex_ground	FedEx Ground	\N
591	690635	2025-10-15	marina@wafamilydentistry.com	shipped	225006630	1	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Marina Zavala	Burlington Family Dentistry	1250 S Burlington Blvd	\N	Burlington	WA	98233	US	(360) 755-5600	Marina Zavala	Burlington Family Dentistry	1250 S Burlington Blvd	\N	Burlington	WA	98233	US	(360) 755-5600	fedex	556346	fedex_ground	FedEx Ground	\N
42	686995	2025-09-30	office@channingdental.com	shipped	221230615	9	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	karol duran	karol duran	2240 Channing Way	\N	Berkeley	CA	94704	US	(510) 845-6494	karol duran	karol duran	2240 Channing Way	\N	Berkeley	CA	94704	US	(510) 845-6494	fedex	556346	fedex_ground	FedEx Ground	\N
43	687005	2025-09-30	rpreachers@dentalcarealliance.com	shipped	220967480	5	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Dental Care Alliance	Rye Smiles for Life Fairfax	10614 Warwick Ave.	\N	FAIRFAX	VA	22030	US	(703) 273-5354	Dental Care Alliance	Rye Smiles for Life Fairfax	10614 Warwick Ave.	\N	FAIRFAX	VA	22030	US	(703) 273-5354	fedex	556346	fedex_ground	FedEx Ground	\N
44	687015	2025-09-30	crystal@drphildentist.com	shipped	220967483	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Phillip Everett	Phillip Everett DDS	2100 W. Michigan Ave	\N	Midland	TX	79701	US	(432) 683-5601	Phillip Everett	Phillip Everett DDS	2100 W. Michigan Ave	\N	Midland	TX	79701	US	(432) 683-5601	fedex	556346	fedex_ground	FedEx Ground	\N
45	687025	2025-09-30	thomascollins1303@yahoo.com	shipped	220968908	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Thomas Collins	Dr. Thomas Collins DDS	1303 West Maple Street\nSuite 106	\N	North Canton	OH	44720	US	(330) 497-7999	Thomas Collins	Dr. Thomas Collins DDS	1303 West Maple Street\nSuite 106	\N	North Canton	OH	44720	US	(330) 497-7999	fedex	556346	fedex_ground	FedEx Ground	\N
46	687035	2025-09-30	info@vacekdentistry.com	shipped	220971690	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Craig Vacek	VFD Innovative Dental- TB	343 N. Cotner Blvd	\N	Lincoln	NE	68505	US	(402) 466-1914	Craig Vacek	VFD Innovative Dental- TB	343 N. Cotner Blvd	\N	Lincoln	NE	68505	US	(402) 466-1914	fedex	556346	fedex_ground	FedEx Ground	\N
47	687045	2025-09-30	admin@oefingerdental.com	shipped	220971691	6	0	ShipStation Manual	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Jessica Burns	OEFINGER DENTAL & ASSOCIATES	13221 NW MILITARY HWY	\N	SAN ANTONIO	TX	78231-1840	US	(210) 492-5668	Jessica Burns	Oefinger Dental & Associates	13221 NW Military Hwy	\N	San Antonio	TX	78231	US	(210) 492-5668	fedex	556346	fedex_ground	FedEx Ground	\N
48	687055	2025-09-30	rcovattodmd@gmail.com	shipped	220972810	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Richard Covatto	Covatto Family Dentistry	3572 Brodhead Road	\N	Monaca	PA	15061	US	(724) 728-7576	Richard Covatto	Covatto Family Dentistry	3572 Brodhead Road	\N	Monaca	PA	15061	US	(724) 728-7576	fedex	556346	fedex_ground	FedEx Ground	\N
49	687075	2025-09-30	reedmaiers@gmail.com	shipped	220990967	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Reed Maiers	Greenhill Family Dental	4507 Chadwick Road	\N	Cedar Falls	IA	50613	US	(319) 266-1433	Reed Maiers	Greenhill Family Dental	4507 Chadwick Road	\N	Cedar Falls	IA	50613	US	(319) 266-1433	fedex	556346	fedex_ground	FedEx Ground	\N
50	687085	2025-09-30	laureldentalgroupmsbills@gmail.com	shipped	220995322	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Stone Thames	Laurel Dental Group	1615 old Amy rd	\N	Laurel	MS	39440	US	601-649-2010	Stone Thames	Laurel Dental Group	1615 old Amy rd	\N	Laurel	MS	39440	US	601-649-2010	fedex	556346	fedex_ground	FedEx Ground	\N
51	687095	2025-09-30	admin@sanjosedentist.com	shipped	221000390	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Steve Lim- TB	STEVE S. LIM, DMD. A DENTAL CORPORATION	105 N. BASCOM AVE. STE 201	\N	SAN JOSE	CA	95128	US	(415) 794-8681	Steve Lim- TB	STEVE S. LIM, DMD. A DENTAL CORPORATION	105 N. BASCOM AVE. STE 201	\N	SAN JOSE	CA	95128	US	(415) 794-8681	fedex	556346	fedex_ground	FedEx Ground	\N
52	687105	2025-09-30	staff@cccid.net	shipped	221001963	2	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Flavio Rasetto	CCCID	5454 Wisconsin Ave\nSte 1500	\N	Chevy Chase	MD	20815	US	(301) 652-9717	Flavio Rasetto	CCCID	8605 Fenway Road	\N	Bethesda	MD	20817	US	3016529717	fedex	556346	fedex_ground	FedEx Ground	\N
53	687125	2025-09-30	familydentistry@kodiakfamily.com	shipped	221230553	18	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Brandon Price	Family Dentistry of Kodiak	1317 Mill Bay Road	\N	Kodiak	AK	99615	US	(907) 486-3291	Brandon Price	Family Dentistry of Kodiak	1317 Mill Bay Road	\N	Kodiak	AK	99615	US	(907) 486-3291	fedex	556346	fedex_ground	FedEx Ground	\N
54	687145	2025-09-30	docdentalic@gmail.com	shipped	221139195	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Kerry Ragbir	Doc's Dental Implants and Crowns	1451 W. Airport Freeway\nSte #2	\N	Irving	TX	75062	US	(682) 774-6299	Kerry Ragbir	Doc's Dental Implants and Crowns	1451 W. Airport Freeway\nSte #2	\N	Irving	TX	75062	US	(682) 774-6299	fedex	556346	fedex_ground	FedEx Ground	\N
55	687155	2025-09-30	records@midtownparkfd.com	shipped	221139196	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Michael Giather	Midtown Park Dental	1451 Union Ave\nSte 130	\N	Memphis	TN	38104	US	(901) 272-1065	Michael Giather	Midtown Park Dental	1451 Union Ave\nSte 130	\N	Memphis	TN	38104	US	(901) 272-1065	fedex	556346	fedex_ground	FedEx Ground	\N
56	687175	2025-09-30	birmingham@drdipilla.com	shipped	221139197	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Robert DiPilla	Aestheitc Dentitstry by DiPilla	720 North Old Woodword Ave\nSte 100	\N	Birmingham	MI	48009	US	(248) 646-0442	Robert DiPilla	Aestheitc Dentitstry by DiPilla	720 North Old Woodword Ave\nSte 100	\N	Birmingham	MI	48009	US	(248) 646-0442	fedex	556346	fedex_ground	FedEx Ground	\N
57	687185	2025-09-30	jean@eghdds.com	shipped	221139198	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Alexander Nguyen	Legacy Dental	800 First Ave Sw	\N	Austin	MN	55912	US	5074378208	Alexander Nguyen	Legacy Dental	800 First Ave Sw	\N	Austin	MN	55912	US	5074378208	fedex	556346	fedex_ground	FedEx Ground	\N
58	687195	2025-09-30	reception@doverdental.com	shipped	221139199	1	0	ShipStation Manual	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Kate Sahafi	DOVER DENTAL	355 PLACENTIA AVE STE 300	\N	NEWPORT BEACH	CA	92663-3304	US	(949) 548-0966	Billing Billing	Billing	26202 Hitching Rail Road	\N	Laguna Hills	CA	92653	US	(949) 548-0966	fedex	556346	fedex_ground	FedEx Ground	\N
59	687205	2025-09-30	dentalcareofantioch@gmail.com	shipped	221139200	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Elika Mirzaagha	Dental Care of Antioch	3432 Hillcrest Ave\nSuite 250	\N	Antioch	CA	94531	US	(925) 754-2145	Elika Mirzaagha	BILLING	44 Stone Creek Place	\N	Alamo	CA	94507	US	9257542145	fedex	556346	fedex_ground	FedEx Ground	\N
60	687245	2025-09-30	info@dougchadwickdds.com	shipped	221139201	15	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Tracy Chadwick	Doug Chadwick DDS	123 SE Douglas St.	\N	Newport	OR	97365	US	(832) 722-9741	Doug Chadwick	Doug Chadwick DDS	334 NW High St	\N	Newport	OR	97365	US	8326892046	fedex	556346	fedex_ground	FedEx Ground	\N
61	687265	2025-09-30	dryvonne@northbaysmiles.com	shipped	221139202	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Yvonne Szyperski	North Bay Smiles	1580 East Washington Street\nSuite 101	\N	Petaluma	CA	94954	US	7077634122	Yvonne Szypereski	NBS	1580 E Washington #101	\N	Petaluma	CA	94954	US	707-7763-4122	fedex	556346	fedex_ground	FedEx Ground	\N
62	687275	2025-09-30	doctor@avdoffice.com	shipped	221139204	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Heather Beaty	Alta Vista Dental	196 Lincoln Way	\N	Auburn	CA	95603	US	(530) 885-3368	Heather Beaty	Alta Vista Dental	196 Lincoln Way	\N	Auburn	CA	95603	US	(530) 885-3368	fedex	556346	fedex_ground	FedEx Ground	\N
63	687285	2025-10-01	roberttaylordds@taylordds.org	shipped	221156452	2	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Jennifer Westendorf	Dr. Robert M Taylor III	1610 S Euclid	\N	Bay City	MI	48706	US	(989) 684-9110	Jennifer Westendorf	Dr. Robert M Taylor III	1610 S Euclid	\N	Bay City	MI	48706	US	(989) 684-9110	fedex	556346	fedex_ground	FedEx Ground	\N
64	687295	2025-10-01	support@harbourdental.care	shipped	221167940	3	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Karen McElroy	Harbour dental care	75 san marco ave	\N	St Augustine	FL	32084	US	(904) 810-1002	Karen McElroy	Harbour dental care	75 san marco ave	\N	St Augustine	FL	32084	US	(904) 810-1002	fedex	556346	fedex_ground	FedEx Ground	\N
65	687305	2025-10-01	info@caredentalco.com	shipped	221169385	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Care Dental	Care Dental	7300 East Arapahoe RD\nSTE 500	\N	Centennial	CO	80112	US	(720) 638-6361	Elevate Dental	Care Dental Office	1801 Wewatta St	\N	Denver	CO	80202	US	3039953753	fedex	556346	fedex_ground	FedEx Ground	\N
66	687315	2025-10-01	mjskovir@gmail.com	shipped	221184792	16	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Michael Skovira	Old Trolley Dental Associates	600 Old Trolley Rd	\N	Summerville	SC	29485	US	(843) 871-2971	Michael Skovira	Old Trolley Dental Associates	600 Old Trolley Rd	\N	Summerville	SC	29485	US	(843) 871-2971	fedex	556346	fedex_ground	FedEx Ground	\N
67	687325	2025-10-01	frontdesk@abingtonfamilydentistry.com	shipped	221191661	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Timothy McGuirman	Abington Family Dentistry PC	314 N State St	\N	Clarks Summit	PA	18411	US	(570) 586-6500	Timothy McGuirman	Abington Family Dentistry PC	314 N State St	\N	Clarks Summit	PA	18411	US	(570) 586-6500	fedex	556346	fedex_ground	FedEx Ground	\N
68	687335	2025-10-01	info@churchstreetdentalny.com	shipped	221197163	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Barbora Valerio	Church Street Dental	3144 Church Street\nP O Box 25	\N	Caledonia	NY	14423	US	(585) 538-2130	Barbora Valerio	Church Street Dental	3144 Church Street\nP O Box 25	\N	Caledonia	NY	14423	US	(585) 538-2130	fedex	556346	fedex_ground	FedEx Ground	\N
69	687345	2025-10-01	devon@joplindental.com	shipped	221200002	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Grant Kirk	Joplin Family Dental	4402 E 32nd St B	\N	Joplin	MO	64804	US	(417) 781-2900	Grant Kirk	Joplin Family Dental	4402 E 32nd St B	\N	Joplin	MO	64804	US	(417) 781-2900	fedex	556346	fedex_ground	FedEx Ground	\N
70	687355	2025-10-01	ADRIGITSCH@GMAIL.COM	shipped	221206638	2	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Robert Ritter	RITTER AND RAMSEY	500 UNIVERSITY BLVD\n SUITE 109	\N	Jupiter	FL	33458	US	(561) 704-8820	Robert Ritter	RITTER AND RAMSEY	500 UNIVERSITY BLVD\n SUITE 109	\N	Jupiter	FL	33458	US	(561) 704-8820	fedex	556346	fedex_ground	FedEx Ground	\N
71	687365	2025-10-01	toothbayharbor@me.com	shipped	221214652	3	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Toby Clarkson	Boothbay Family Dentistry	732 Wiscasset Road	\N	Boothbay	ME	04537	US	(207) 633-4243	Toby Clarkson	Boothbay Family Dentistry	732 Wiscasset Road	\N	Boothbay	ME	04537	US	(207) 633-4243	fedex	556346	fedex_ground	FedEx Ground	\N
72	687375	2025-10-01	monroe@wafamilydentistry.com	shipped	221230297	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Ashley Felton	Elevate Monroe	19071 State Hwy 2	\N	Monroe	WA	98272	US	(360) 794-9000	Ashley Felton	Elevate Monroe	19071 State Hwy 2	\N	Monroe	WA	98272	US	(360) 794-9000	fedex	556346	fedex_ground	FedEx Ground	\N
73	687385	2025-10-01	backofficevdc@gmail.com	shipped	221224180	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Matthew Harmon	The Village Dental Center	13802 W Camino del Sol\nSuite #101	\N	Sun City West	AZ	85375	US	(623) 583-0151	Matthew Harmon	The Village Dental Center	13802 W Camino del Sol\nSuite #101	\N	Sun City West	AZ	85375	US	(623) 583-0151	fedex	556346	fedex_ground	FedEx Ground	\N
74	687395	2025-10-01	smile@mydaytonadentist.com	shipped	221231699	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	David Lloyd	Indigo Dental	139 EXECUTIVE CIR \nste 101	\N	Daytona Beach	FL	32114	US	(386) 253-3629	David Lloyd	Indigo Dental	139 EXECUTIVE CIR \nste 101	\N	Daytona Beach	FL	32114	US	(386) 253-3629	fedex	556346	fedex_ground	FedEx Ground	\N
75	687405	2025-10-01	victorialuebenko@gmail.com	shipped	221236487	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Victoria Benko	McCandless Dental Care	5900 Corporate Dr\nSte 220	\N	Pittsburgh	PA	15237	US	(412) 847-1420	Victoria Benko	McCandless Dental Care	5900 Corporate Dr\nSte 220	\N	Pittsburgh	PA	15237	US	(412) 847-1420	fedex	556346	fedex_ground	FedEx Ground	\N
76	687415	2025-10-01	doclaszlo@gmail.com	shipped	221238887	2	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Mark Laszlo	Mark Laszlo	3714 Sashabaw Rd	\N	Waterford	MI	48329	US	(248) 674-4171	Mark Laszlo	Laszlo	8687 Alen Rd	\N	Clarkston	MI	48348	US	2486724894	fedex	556346	fedex_ground	FedEx Ground	\N
77	687425	2025-10-01	brighamdental@hotmail.com	shipped	221240989	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Brent Butler	Brigham City Dental	305 No. Main St.	\N	Brigham City	UT	84302	US	(435) 734-2626	Brent Butler	Brigham City Dental	305 No. Main St.	\N	Brigham City	UT	84302	US	(435) 734-2626	fedex	556346	fedex_ground	FedEx Ground	\N
78	687435	2025-10-01	aaydboise@gmail.com	shipped	221245775	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Taylor Clark	All About You Dental	4274 N Eagle Rd	\N	Boise	ID	83713	US	(208) 938-8228	Taylor Clark	All About You Dental	4274 N Eagle Rd	\N	Boise	ID	83713	US	(208) 938-8228	fedex	556346	fedex_ground	FedEx Ground	\N
79	687455	2025-10-01	cougar.dental@yahoo.com	shipped	221250832	3	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Corbin Matthews	Cougar Dental	835 N 700 E	\N	Provo	UT	84606	US	8013737700	Todd Groesbeck	Dentive	5152 Edgewood Dr STE 350	\N	Provo	UT	84604	US	8013737700	fedex	556346	fedex_ground	FedEx Ground	\N
80	687465	2025-10-01	shallowford.winnsmiles@gmail.com	shipped	221253770	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Brad Winn	Winn Smiles- Shalowford	2217 Olan Mills Dr	\N	Chattanooga	TN	37421	US	(423) 894-5607	Brad Winn	Winn Smiles	148 Stuart Crossing NW	\N	Cleveland	TN	37312	US	4234726482	fedex	556346	fedex_ground	FedEx Ground	\N
81	687485	2025-10-01	Hdsleadassistant@gmail.com	shipped	221273193	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Makenzi Talbot	Holladay Dental Studio	4888 s highland drive	\N	Holladay	UT	84117	US	(801) 277-9213	Makenzi Talbot	Holladay Dental Studio	4888 s highland drive	\N	Holladay	UT	84117	US	(801) 277-9213	fedex	556346	fedex_ground	FedEx Ground	\N
82	687545	2025-10-01	downtown@sunrise.dental	shipped	221283358	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Paige Hawkins	Sunrise Dental Care	951 Riverfront Parkway\nSuite 301	\N	Chattanooga	TN	37402	US	(423) 266-4757	Paige Hawkins	Sunrise Dental Care	951 Riverfront Parkway\nSuite 301	\N	Chattanooga	TN	37402	US	(423) 266-4757	fedex	556346	fedex_ground	FedEx Ground	\N
102	687805	2025-10-02	contact@laytonlakesdental.com	shipped	221552729	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Sneha Subramanian	Layton Lakes Dental	3230 S Gilbert Rd #4	\N	Chandler	AZ	85286	US	(480) 306-5506	Sneha Subramanian	Layton Lakes Dental	3423 E Bluebird PL	\N	Chandler	AZ	85286	US	4803065506	fedex	556346	fedex_ground	FedEx Ground	\N
83	687555	2025-10-01	info@texasstardental.com	shipped	221284689	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Lauren Austin	Texas Star Dental	142 Vintage Park Blvd Suite E	\N	Houston	TX	77070	US	(281) 251-8181	Lauren Austin	Texas Star Dental	142 Vintage Park Blvd Suite E	\N	Houston	TX	77070	US	(281) 251-8181	fedex	556346	fedex_ground	FedEx Ground	\N
84	687585	2025-10-01	painless1@digis.net	shipped	221300929	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Caesar Hearne	Woodland Park Dental	3080 N 1700TH  E\nSte. A	\N	LAYTON	UT	84040	US	8017284688	Caesar Hearne	Woodland Park Dental	3080 N 1700TH  E\nSte. A	\N	LAYTON	UT	84040	US	8017284688	fedex	556346	fedex_ground	FedEx Ground	\N
85	687595	2025-10-01	general@granadadental.com	shipped	221306668	2	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Reza Nazari DDS	Granada Dental	2677 Old First St	\N	Livermore	CA	94550	US	(925) 447-0324	Reza Nazari DDS	Granada Dental	2677 Old First St	\N	Livermore	CA	94550	US	(925) 447-0324	fedex	556346	fedex_ground	FedEx Ground	\N
109	100504	2025-10-01		shipped	221309303	1	0	ShipStation Manual	2025-10-02 21:37:33	2025-10-15 05:23:36.295358	\N	Dental Associates of Lake Jackson	DENTAL ASSOCIATES OF LAKE JACKSON	201 OAK DR S STE 206	\N	LAKE JACKSON	TX	77566-5627	US	\N	Dental Associates of Lake Jackson	\N	\N	\N	\N	\N	\N		\N	fedex	556346	fedex_ground	FedEx Ground	\N
86	687605	2025-10-01	alexbrgr82@gmail.com	shipped	221424967	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Alex Berger	Alex Berger DDS	662 Las Gallinas Ave.	\N	San Rafael	CA	94903	US	7074863505	Alex Berger	Alex Berger DDS	662 Las Gallinas Ave.	\N	San Rafael	CA	94903	US	7074863505	fedex	556346	fedex_ground	FedEx Ground	\N
87	687615	2025-10-01	jamie@northstardentalco.com	shipped	221424893	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	James Muldoon	Northstar Dental	860 Tabor Street\nSuite 100	\N	Lakewood	CO	80403	US	(303) 234-1112	James Muldoon	Northstar Dental	860 Tabor Street\nSuite 100	\N	Lakewood	CO	80403	US	(303) 234-1112	fedex	556346	fedex_ground	FedEx Ground	\N
88	687625	2025-10-01	shelly@northgatedentalcare.com	shipped	221423633	3	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Dr. Joshua Carter	Northgate Dental Care	1016 middle creek parkway	\N	Colorado Springs	CO	80921	US	719-488-2292	Dr. Joshua Carter	Northgate Dental Care	1016 middle creek parkway	\N	Colorado Springs	CO	80921	US	719-488-2292	fedex	556346	fedex_ground	FedEx Ground	\N
89	687635	2025-10-01	capenerdental@hotmail.com	shipped	221423484	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Randell Capener	Randell M Capener DMD	515 W Forest St	\N	Brigham City	UT	84302	US	(435) 232-6728	Randell Capener	Randell M Capener DMD	515 W Forest St	\N	Brigham City	UT	84302	US	(435) 232-6728	fedex	556346	fedex_ground	FedEx Ground	\N
90	687645	2025-10-02	dmd@cummingdentalcare.com	shipped	221453324	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	J. Clay Skognes	Cumming Dental Care PC	416 Pirkle Ferry Road\nBlg G, Suite 300	\N	Cumming	GA	30040	US	(770) 889-1990	J. Clay Skognes	Cumming Dental Care PC	416 Pirkle Ferry Road\nBlg G, Suite 300	\N	Cumming	GA	30040	US	(770) 889-1990	fedex	556346	fedex_ground	FedEx Ground	\N
91	687665	2025-10-02	drking@drkingdentistry.com	shipped	221462730	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	David King	King Dental	1108 Gleneagles Dr.	\N	Huntsville	AL	35801	US	(256) 457-7466	David King	King Dental	1108 Gleneagles Dr.	\N	Huntsville	AL	35801	US	(256) 457-7466	fedex	556346	fedex_ground	FedEx Ground	\N
92	687675	2025-10-02	madeleinegrothdds@gmail.com	shipped	221466075	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Madeline Groth	Madeline Groth, DMD LLC	544 jefferson st	\N	lafayette	LA	70501	US	337-232-1070	Madeline Groth	Madeline Groth, DMD LLC	544 jefferson st	\N	lafayette	LA	70501	US	337-232-1070	fedex	556346	fedex_ground	FedEx Ground	\N
93	687685	2025-10-02	ggsmiledoc@dothancosmeticdentistry.com	shipped	221469791	2	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Geoff Gaunt	Dophan Cosmetic Dentistry	2431 West Main Street\nSte 401	\N	Dophan	AL	36301	US	(334) 673-7440	Geoff Gaunt	Dophan Cosmetic Dentistry	2431 West Main Street\nSte 401	\N	Dophan	AL	36301	US	(334) 673-7440	fedex	556346	fedex_ground	FedEx Ground	\N
94	687695	2025-10-02	dentists@tlcdentalfw.com	shipped	221471140	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Savithri Raju	TLC DENTAL LLC	7908 Carnegie Blvd	\N	Fort Wayne	IN	46804	US	(260) 423-2525	Savithri Raju	TLC DENTAL LLC	126 Chestnut Hills Parkway	\N	Fort Wayne	IN	46814	US	2604232525	fedex	556346	fedex_ground	FedEx Ground	\N
95	687705	2025-10-02	info@smilesbyhart.com	shipped	221472083	15	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Dr.John Hart	c/o Smiles by Hart	4700 Centre Ave	\N	Pittsburgh	PA	15213	US	4126818011	Dr. John Hart	Smiles by Hart	4700 Centre Ave	\N	Pittsburgh	PA	15213	US	(412) 681-8011	fedex	556346	fedex_ground	FedEx Ground	\N
96	687715	2025-10-02	tulanefamilydentistry@gmail.com	shipped	221476932	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	William Shelton	Tulane Family Dentistry-TB	1600 St Charles Ave\nSte 201	\N	New orleans	LA	70130	US	504-304-9929	William Shelton	Tulane Family Dentistry-TB	1600 St Charles Ave\nSte 201	\N	New orleans	LA	70130	US	504-304-9929	fedex	556346	fedex_ground	FedEx Ground	\N
97	687725	2025-10-02	lexiebrazeale@singingriverdentistry.net	shipped	221492173	4	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Jimmy Gardiner	Singing River Dentistry - Tuscumbia	121 East 6th Street	\N	Tuscumbia	AL	35674	US	(256) 383-0377	James Maples James Maples	singing river	121 East 6th Street	\N	Tuscumbia	AL	35674	US	256-383-0377	fedex	556346	fedex_ground	FedEx Ground	\N
98	687735	2025-10-02	drcase@fdhealth.com	shipped	221495177	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	David Case	Family Dental Health	6333 S. Macadam Ave\nSte. 107	\N	Portland	OR	97239	US	(503) 977-3400	David Case	Family Dental Health	6333 S. Macadam Ave\nSte. 107	\N	Portland	OR	97239	US	(503) 977-3400	fedex	556346	fedex_ground	FedEx Ground	\N
99	687775	2025-10-02	drgreg@stepkafamilydental.com	shipped	221519274	6	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Gregory Stepka	Stepka Family Dental INC	501 Great Road\nSuite 207	\N	North Smithfield	RI	02896	US	(401) 766-9857	GREGORY STEPKA	Stepka Family Dental	4 Torrey Road	\N	Sutton	MA	01590	US	4017669857	fedex	556346	fedex_ground	FedEx Ground	\N
100	687785	2025-10-02	info@synergydentalgroup.net	shipped	221530150	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Kimberly Hubenette	Synergy Dental Group	660 Third Street West	\N	Sonoma	CA	95476	US	(707) 938-9066	Kimberly Hubenette	Synergy Dental Group	660 Third Street West	\N	Sonoma	CA	95476	US	(707) 938-9066	fedex	556346	fedex_ground	FedEx Ground	\N
101	687795	2025-10-02	capenerdental@hotmail.com	shipped	221549747	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Randell Capener	Randell M Capener DMD	515 W Forest St	\N	Brigham City	UT	84302	US	(435) 232-6728	Randell Capener	Randell M Capener DMD	515 W Forest St	\N	Brigham City	UT	84302	US	(435) 232-6728	fedex	556346	fedex_ground	FedEx Ground	\N
594	690665	2025-10-15	Willdenfamilydental@comcast.net	shipped	225006638	5	\N	X-Cart	2025-10-15 14:22:53.361306	2025-10-16 17:27:39.325556	\N	Ryan Willden	Willden Family Dental	10654 River Heights Drive\nSte 330	\N	South Jordan	UT	84095	US	(801) 446-4668	Ryan Willden	Willden Family Dental	10654 River Heights Drive\nSte 330	\N	South Jordan	UT	84095	US	(801) 446-4668	fedex	556346	fedex_ground	FedEx Ground	\N
103	687815	2025-10-02	purewellpharmacy1@gmail.com	shipped	221576000	1	\N	X-Cart	2025-10-02 20:19:54	2025-10-15 05:23:36.295358	\N	Davik Saha	Purewell	5413 Airport Pulling rd N	\N	Naples	FL	34109	US	(239) 591-5738	Davik Saha	Purewell	5413 Airport Pulling rd N	\N	Naples	FL	34109	US	(239) 591-5738	fedex	556346	fedex_ground	FedEx Ground	\N
104	687825	2025-10-02	cda@greenparkdentistry.com	shipped	221588580	15	\N	X-Cart	2025-10-02 20:50:06	2025-10-15 05:23:36.295358	\N	Kristi Paris	Green Park Dentistry	1331 4th St Dr NW\nSuite A	\N	Hickory	NC	28601	US	(828) 327-7502	Kristi Paris	Green Park Dentistry	1331 4th St Dr NW\nSuite A	\N	Hickory	NC	28601	US	(828) 327-7502	fedex	556346	fedex_ground	FedEx Ground	\N
105	687835	2025-10-02	cda@greenparkdentistry.com	shipped	221588581	1	\N	X-Cart	2025-10-02 20:50:06	2025-10-15 05:23:36.295358	\N	Kristi Paris	Green Park Dentistry	1331 4th St Dr NW\nSuite A	\N	Hickory	NC	28601	US	(828) 327-7502	Kristi Paris	Green Park Dentistry	1331 4th St Dr NW\nSuite A	\N	Hickory	NC	28601	US	(828) 327-7502	fedex	556346	fedex_ground	FedEx Ground	\N
278	687855	2025-10-02	starsmilestexas@gmail.com	shipped	221735760	1	\N	X-Cart	2025-10-02 22:35:37	2025-10-15 05:23:36.295358	\N	Quyen Chau	Star smiles Cosmetic and Family Dentistry	7700 Highway 6 N, #106	\N	Houston	TX	77095	US	(281) 550-5757	Quyen Chau	Star smiles Cosmetic and Family Dentistry	7700 Highway 6 N, #106	\N	Houston	TX	77095	US	(281) 550-5757	fedex	556346	fedex_ground	FedEx Ground	\N
108	686255	2025-09-25	drdeleonsmile@hotmail.com	shipped	221546565	2	0	ShipStation Manual	2025-10-02 21:37:33	2025-10-15 05:23:36.295358	\N	patti  de leon	DE LEON DENTISTRY	1942 HARBOR BLVD	\N	COSTA MESA	CA	92627-2669	US	(949) 631-1000	patti  de leon	de leon dentistry	1942 harbor blvd	\N	costa mesa	CA	92627	US	(949) 631-1000	fedex	556346	fedex_2day	FedEx 2Day	\N
277	100505	2025-10-02	cb9540@benco.com	shipped	221567336	8	0	ShipStation Manual	2025-10-02 22:04:53	2025-10-15 05:23:36.295358	\N	Courtney Brahm	Benco	3424 CENTENNIAL DR STE 150	\N	FORT WAYNE	IN	46808-4523	US	8552556722	Courtney Brahm	\N	\N	\N	\N	\N	\N		8552556722	fedex	556346	fedex_ground	FedEx Ground	\N
107	687845	2025-10-02	pgabedmd@gmail.com	shipped	221613718	2	\N	X-Cart	2025-10-02 21:20:14	2025-10-15 05:23:36.295358	\N	Paul Gabriel	Paul B Gabriel DMD PC	2500 Brooktree Rd\nSuite 100	\N	WEXFORD	PA	15090	US	(724) 935-2100	Paul Gabriel	Paul B Gabriel DMD PC	2500 Brooktree Rd\nSuite 100	\N	WEXFORD	PA	15090	US	(724) 935-2100	fedex	556346	fedex_ground	FedEx Ground	\N
279	687865	2025-10-03	Phil.J.SnyderDDS@gmail.com	shipped	221755391	1	\N	X-Cart	2025-10-03 13:07:54	2025-10-15 05:23:36.295358	\N	Terri Lally	Dr PJ Snyder	250 Debartolo Place	\N	Boardman	OH	44512	US	(330) 965-0000	Terri Lally	Dr PJ Snyder	250 Debartolo Place	\N	Boardman	OH	44512	US	(330) 965-0000	fedex	556346	fedex_ground	FedEx Ground	\N
280	687885	2025-10-03	dryazdani@revivemetoday.com	shipped	221797210	2	\N	X-Cart	2025-10-03 15:58:09	2025-10-15 05:23:36.295358	\N	Shila Yazdani	Revive Dentistry	3301 new mexico ave NW\nSuite 108	\N	washington	DC	20016	US	(202) 363-3399	michael mortazie-tb	Revive Dentistry	1011 eaton dr	\N	mclean	VA	22102	US	(202) 363-3399	fedex	556346	fedex_ground	FedEx Ground	\N
281	687895	2025-10-03	newbraunfels2bf@pacden.com	cancelled	221824914	6	\N	X-Cart	2025-10-03 17:06:02	2025-10-15 05:23:36.295358	\N	Robert Krantz	New Braunfels Modern Dentistry	244 FM 306 Ste 118	\N	New Braunfels	TX	78130	US	(830) 201-1223	Robert Krantz	New Braunfels Modern Dentistry	244 FM 306 Ste 118	\N	New Braunfels	TX	78130	US	(830) 201-1223	fedex	556346	fedex_ground	FedEx Ground	\N
283	687905	2025-10-03	ravikumarr@pacden.com	cancelled	221826272	4	\N	X-Cart	2025-10-03 17:14:39	2025-10-15 05:23:36.295358	\N	RAKSHITH ARAKOTARAM RAVIKUMAR	Bastrop Modern Dentistry	1670 HWY 71 E, STE A	\N	BASTROP	TX	78602	US	(512) 240-6496	RAKSHITH ARAKOTARAM RAVIKUMAR	Bastrop Modern Dentistry	1670 HWY 71 E, STE A	\N	BASTROP	TX	78602	US	(512) 240-6496	fedex	556346	fedex_ground	FedEx Ground	\N
284	687915	2025-10-03	westpointemoderndentistry@smilegeneration.com	cancelled	221826275	6	\N	X-Cart	2025-10-03 17:14:39	2025-10-15 05:23:36.295358	\N	Matthew Gesell	West Pointe	1659 state HWY 46 W \nSte 180	\N	New Braunfels	TX	78132	US	(830) 625-6600	Matthew Gesell	West Pointe	1659 state HWY 46 W \nSte 180	\N	New Braunfels	TX	78132	US	(830) 625-6600	fedex	556346	fedex_ground	FedEx Ground	\N
285	687935	2025-10-03	Jmorrisdds@comcast.net	shipped	221951872	1	\N	X-Cart	2025-10-04 03:02:23	2025-10-15 05:23:36.295358	\N	Jennifer Morris	CCPDG	13100 CORTE DIEGO	\N	Salinas	CA	93908	US	3105921627	Jennifer Morris	CCPDG	13100 CORTE DIEGO	\N	Salinas	CA	93908	US	3105921627	fedex	556346	fedex_ground	FedEx Ground	\N
287	687945	2025-10-06	admin@drdancassidy.com	shipped	222399365	1	\N	X-Cart	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Daniel Cassidy	Daniel E Cassidy DDS	2835 Duke St	\N	Alexandria	VA	22314	US	(703) 370-2333	Daniel Cassidy	Daniel E Cassidy DDS	2835 Duke St	\N	Alexandria	VA	22314	US	(703) 370-2333	fedex	556346	fedex_ground	FedEx Ground	\N
288	687955	2025-10-06	katy@lhdmpls.com	shipped	222400685	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Katy Pilcher	Linden Hills Dentistry	4289 Sheridan Ave S.	\N	Minneapolis	MN	55410	US	(612) 922-6164	Katy Pilcher	Linden Hills Dentistry	4289 Sheridan Ave S.	\N	Minneapolis	MN	55410	US	(612) 922-6164	fedex	556346	fedex_ground	FedEx Ground	\N
289	687965	2025-10-06	Alegu10@hotmail.com	shipped	222400691	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Alan Gutierrez	Whittier Dental Arts	13203 E Hadley St Ste 106	\N	Whittier	CA	90601	US	(562) 907-6000	Alan Gutierrez	Whittier Dental Arts	13203 E Hadley St Ste 106	\N	Whittier	CA	90601	US	(562) 907-6000	fedex	556346	fedex_ground	FedEx Ground	\N
290	687975	2025-10-06	contact@kleigerdentistry.com	shipped	222400698	3	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Trish Fredrick	Ean Kleiger DDS	319 S. Moorpark Rd.	\N	Thousand Oaks	CA	91361	US	(805) 494-4234	Trish Fredrick	Ean Kleiger DDS	319 S. Moorpark Rd.	\N	Thousand Oaks	CA	91361	US	(805) 494-4234	fedex	556346	fedex_ground	FedEx Ground	\N
291	687985	2025-10-06	georgiaorders@fullsmiledental.com	shipped	222400705	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Dr. Tsang	Full Smile Dental Georgia	3609 S. Georgia St.	\N	Amarillo	TX	79109	US	(806) 381-3447	Full Smile Management	Billing	2201 Civic Circle\nSte 600	\N	Amarillo	TX	79109	US	806-381-3447	fedex	556346	fedex_ground	FedEx Ground	\N
292	687995	2025-10-06	delaney@smiledailey.com	shipped	222400713	7	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Lauren Shelnut	Smile Dailey Dental	17200 Chenal Pkwy\nSte 250	\N	Little Rock	AR	72211	US	(501) 448-0032	Lauren Shelnut	Smile Dailey Dental	17200 Chenal Pkwy\nSte 250	\N	Little Rock	AR	72211	US	(501) 448-0032	fedex	556346	fedex_ground	FedEx Ground	\N
293	688005	2025-10-06	grazianodds@gmail.com	shipped	222400725	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Caitlin Graziano	Deitz Family Dental	108 Everett Rd	\N	Albany	NY	12205	US	(518) 458-1723	Caitlin Graziano	Deitz Family Dental	108 Everett Rd	\N	Albany	NY	12205	US	(518) 458-1723	fedex	556346	fedex_ground	FedEx Ground	\N
294	688015	2025-10-06	Ericsmithdds@hotmail.com	shipped	222400731	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Eric Smith	Four Seasons Dental, LLC	4465 S. 900 E. #100	\N	Salt Lake City	UT	84124	US	(801) 281-0100	Eric Smith	Four Seasons Dental, LLC	4465 S. 900 E. #100	\N	Salt Lake City	UT	84124	US	(801) 281-0100	fedex	556346	fedex_ground	FedEx Ground	\N
295	688025	2025-10-06	sjeasedental@gmail.com	shipped	222402595	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Brandon Phuong	Ease Dental	2344 Mckee, Suite 20	\N	San Jose	CA	95116	US	(408) 272-4200	Brandon Phuong	Ease Dental	2344 Mckee, Suite 20	\N	San Jose	CA	95116	US	(408) 272-4200	fedex	556346	fedex_ground	FedEx Ground	\N
296	688035	2025-10-06	Rhdentistryom@gmail.com	shipped	222402600	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Michelle Boecker	Rh dentistry of memorial	13210 memorial dr suite 300	\N	Houston	TX	77079	US	(281) 661-1844	Michelle Boecker	Rh dentistry of memorial	13210 memorial dr suite 300	\N	Houston	TX	77079	US	(281) 661-1844	fedex	556346	fedex_ground	FedEx Ground	\N
297	688055	2025-10-06	office@familydentalco.com	shipped	222402604	3	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Melissa Kusiak	Family Dental Co	7311 W 79th St	\N	Overland Park	KS	66204	US	(913) 602-8310	Melissa Kusiak	BILLING	7653 Colonial Street	\N	Prairie Village	KS	66208	US	913-602-8310	fedex	556346	fedex_ground	FedEx Ground	\N
298	688065	2025-10-06	om@macridental.com	shipped	222402610	5	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Chris Macri	Macri Dental	5420 S. Quebec Street\nSuite 203	\N	Greenwood Village	CO	80111	US	(303) 694-0585	Chris Macri	Macri Dental	5420 S. Quebec Street\nSuite 203	\N	Greenwood Village	CO	80111	US	(303) 694-0585	fedex	556346	fedex_ground	FedEx Ground	\N
299	688075	2025-10-06	lbowersoxdds@gmail.com	shipped	222402613	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Lauren Bowersox	Dental Associates of Atlanta	1100 Abernathy Rd. NE\nSuite 1020	\N	Atlanta	GA	30328	US	(770) 804-0616	Lauren Bowersox	Dental Associates of Atlanta	1100 Abernathy Rd. NE\nSuite 1020	\N	Atlanta	GA	30328	US	(770) 804-0616	fedex	556346	fedex_ground	FedEx Ground	\N
300	688085	2025-10-06	carpenteresteydds@yahoo.com	shipped	222402617	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Erin Estey	Estey & Carpenter Dentistry	1806 Orange Tree Lane	\N	Redlands	CA	92374	US	(909) 335-1166	Erin Estey	Estey & Carpenter Dentistry	1806 Orange Tree Lane	\N	Redlands	CA	92374	US	(909) 335-1166	fedex	556346	fedex_ground	FedEx Ground	\N
301	688095	2025-10-06	halliemccallum@premdent.com	shipped	222402621	5	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Christopher Arnold	Premier Dental Center	80 Exerter Road	\N	Jackson	TN	38305	US	(731) 300-3000	Christopher Arnold	Premier Dental Center	7019 HWY 412 S	\N	Bells	TN	38006	US	731-300-3000	fedex	556346	fedex_ground	FedEx Ground	\N
302	688105	2025-10-06	mpomps4@yahoo.com	shipped	222402625	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Mark Pompeani	Mark J Pompeani DDS	22725 Fairview Center Drive\nSte 150	\N	Fairview Park	OH	44126	US	(440) 716-7667	Mark Pompeani	Mark Pompeani DDS	3368 Vineyard Park	\N	Avon	OH	44011	US	4407167667	fedex	556346	fedex_ground	FedEx Ground	\N
303	688145	2025-10-06	info@grinviewsmiles.com	shipped	222403609	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Geoffrey Barnum	Grinview Smiles	901 S. Third st	\N	Grandview	TX	76050	US	(817) 866-2065	Geoffrey Barnum	Billing	301 East Bethesda Road	\N	Burleson	TX	76028	US	8178662065	fedex	556346	fedex_ground	FedEx Ground	\N
304	688155	2025-10-06	ligockidentalgroup@gmail.com	shipped	222403614	6	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Mark Ligocki	Ligocki Dental Group	1S224 Summit Avenue\nSuite 104	\N	Oakbrook Terrace	IL	60181	US	6306208099	Mark Ligocki	Ligocki Dental Group	1S224 Summit Avenue\nSuite 104	\N	Oakbrook Terrace	IL	60181	US	6306208099	fedex	556346	fedex_ground	FedEx Ground	\N
305	688165	2025-10-06	jlai@edgedentalhouston.com	shipped	222403621	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Justin Lai	Edge Dental	15455 Memorial Dr\nSte 400 Edge Dental	\N	HOUSTON	TX	77079	US	(281) 940-8940	Justin Lai	Edge Dental	15455 Memorial Dr\nSte 400 Edge Dental	\N	HOUSTON	TX	77079	US	(281) 940-8940	fedex	556346	fedex_ground	FedEx Ground	\N
306	688175	2025-10-06	info@manyakdental.com	shipped	222403625	10	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Tanya Manyak	Manyak Dental Group- TB	100 South Ellsworth Ave\nSuite #601	\N	San Mateo	CA	94401	US	(650) 342-9941	Tanya Manyak	Manyak Dental Group- TB	100 South Ellsworth Ave\nSuite #601	\N	San Mateo	CA	94401	US	(650) 342-9941	fedex	556346	fedex_ground	FedEx Ground	\N
307	688185	2025-10-06	abbadentdental@gmail.com	shipped	222403631	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Jodi McCarron	Abbadent Dental	3430 Dodge Street\nSuite21	\N	Dubuque	IA	52003	US	(563) 556-8388	Jodi McCarron	Abbadent Dental	3430 Dodge Street\nSuite21	\N	Dubuque	IA	52003	US	(563) 556-8388	fedex	556346	fedex_ground	FedEx Ground	\N
308	688195	2025-10-06	bills@brightdirectiondental.com	shipped	222403635	5	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Jennie Sahm	Center For Advanced Dentistry	8325 South Emerson Avenue\nSuite A	\N	Indianapolis	IN	46237	US	(317) 859-6768	Ruthann Witt	Bright Direction Dental LLC	318 West Adams Street\nSTE 400B	\N	Chicago	IL	60606	US	(312) 560-3351	fedex	556346	fedex_ground	FedEx Ground	\N
309	688205	2025-10-06	appointments@salemdentalartsma.com	shipped	222403641	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Pamela Maragliano-Muniz, DMD	Salem Dental Arts	20 Central St\nSte 111	\N	Salem	MA	01970	US	(978) 741-1640	Pamela Maragliano-Muniz, DMD	Salem Dental Arts	20 Central St\nSte 111	\N	Salem	MA	01970	US	(978) 741-1640	fedex	556346	fedex_ground	FedEx Ground	\N
310	688215	2025-10-06	info@seguinsmiles.com	shipped	222404845	7	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Tiffany Frothingham- TB	Seguin Smiles	1460 Eastwood Dr	\N	Seguin	TX	78155	US	(830) 372-2949	Tiffany Frothingham- TB	Seguin Smiles	1460 Eastwood Dr	\N	Seguin	TX	78155	US	(830) 372-2949	fedex	556346	fedex_ground	FedEx Ground	\N
311	688225	2025-10-06	drdavidmrizk@aol.com	shipped	222404853	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	David Rizk	David M Rizk, DDS	7211 North Mesa\nSte 1N	\N	El Paso	TX	79912	US	(915) 581-0500	David Rizk	David M Rizk, DDS	7211 North Mesa\nSte 1N	\N	El Paso	TX	79912	US	(915) 581-0500	fedex	556346	fedex_ground	FedEx Ground	\N
312	688235	2025-10-06	Ortizfamilydental@gmail.com	shipped	222404858	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Ramon Ortiz	Painted Skies Dental Center	3045 E University Ave Suite B	\N	Las Cruces	NM	88011	US	(575) 521-8720	Ramon Ortiz	Painted Skies Dental Center	3045 E University Ave Suite B	\N	Las Cruces	NM	88011	US	(575) 521-8720	fedex	556346	fedex_ground	FedEx Ground	\N
313	688245	2025-10-06	armenrai@yahoo.com	shipped	222404860	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Aparna Menami	Aparna Menrai, DDS	6541 Crown BLVD\nSuite A	\N	San Jose	CA	95120	US	(408) 226-3870	Aparna Menami	Aparna Menrai, DDS	6541 Crown BLVD\nSuite A	\N	San Jose	CA	95120	US	(408) 226-3870	fedex	556346	fedex_ground	FedEx Ground	\N
314	688255	2025-10-06	admin@craftandcaredental.com	shipped	222404876	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Tyler Bolin	Care & Craft Dental	220 Ruccio Way\nSuite 120	\N	Lexington	KY	40503	US	(859) 309-1095	Tyler Bolin	Care & Craft Dental	220 Ruccio Way\nSuite 120	\N	Lexington	KY	40503	US	(859) 309-1095	fedex	556346	fedex_ground	FedEx Ground	\N
315	688265	2025-10-06	adminassistant@gps.dental	shipped	222404880	5	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Jeffrey Hubbard	Park Cities Family Dentistry	4131 North Central Express Way\nSte 600	\N	Dallas	TX	75204	US	(214) 528-3770	Jeffrey Hubbard	Park Cities Family Dentistry	PO 17151	\N	Jonesboro	AR	72403	US	214-528-3770	fedex	556346	fedex_ground	FedEx Ground	\N
316	688275	2025-10-06	awhite@branforddentalcare.com	shipped	222404886	5	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Maria Hacker	Branford Dental Care	134 Montowese St	\N	Branford	CT	06405	US	(203) 488-7444	Maria Hacker	Branford Dental Care	134 Montowese St	\N	Branford	CT	06405	US	(203) 488-7444	fedex	556346	fedex_ground	FedEx Ground	\N
317	688285	2025-10-06	brockmanfamilydentistry@gmail.com	shipped	222404896	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	John Brockman	Brockman Family Dentistry	11949 Lioness Way\nSuite 200	\N	Parker	CO	80134	US	3037994333	John Brockman	Brockman Family Dentistry	7529 Pine Ridge Trail\nSuite 200	\N	Castle Rock	CO	80108	US	(303) 799-4333	fedex	556346	fedex_ground	FedEx Ground	\N
318	688295	2025-10-06	smyldds@fuse.net	shipped	222404914	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Timothy Pohlman	Timothy Pohlman DDS	2761 Erie Ave	\N	Cincinnati,	OH	45208	US	(513) 871-2989	Timothy Pohlman	Timothy Pohlman DDS	2761 Erie Ave	\N	Cincinnati,	OH	45208	US	(513) 871-2989	fedex	556346	fedex_ground	FedEx Ground	\N
319	688305	2025-10-06	info@deefordentist.com	shipped	222405846	5	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Rewadee Meevasin	Dee for Dentist-TruBlu	8772 S MARYLAND PKWY STE 100	\N	LAS VEGAS	NV	89123	US	(702) 586-7800	Rewadee Meevasin	Dee for Dentist-TruBlu	8772 S MARYLAND PKWY STE 100	\N	LAS VEGAS	NV	89123	US	(702) 586-7800	fedex	556346	fedex_ground	FedEx Ground	\N
320	688315	2025-10-06	lvdentistry702@gmail.com	shipped	222405850	3	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Reevasin Meevasin	Dee for Dentist- Medical District	2421 W Charleston Blvd	\N	Las Vegas	NV	89102	US	(702) 870-3818	Reevasin Meevasin	Dee for Dentist- Medical District	2421 W Charleston Blvd	\N	Las Vegas	NV	89102	US	(702) 870-3818	fedex	556346	fedex_ground	FedEx Ground	\N
321	688325	2025-10-06	uptowndental111@gmail.com	shipped	222405855	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Michelle Crews	Uptown Dental	141 Township Ave\nSuite 111	\N	Ridgeland	MS	39046	US	(769) 257-0399	Michelle Crews	Uptown Dental	111 Waterford Lane	\N	Madison	MS	39110	US	7692570399	fedex	556346	fedex_ground	FedEx Ground	\N
322	688335	2025-10-06	farrwestfamilydental@gmail.com	shipped	222405860	4	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Peggy Ashworth	Farr West Family Dental	1407 N 2000 W	\N	FARR WEST	UT	84404	US	(801) 731-9058	Peggy Ashworth	Farr West Family Dental	1407 N 2000 W	\N	FARR WEST	UT	84404	US	(801) 731-9058	fedex	556346	fedex_ground	FedEx Ground	\N
346	688585	2025-10-06	Blackbearfamilydental@gmail.com	shipped	222563666	1	0	ShipStation Manual	2025-10-06 20:30:26	2025-10-15 05:23:36.295358	\N	Veronica Cooper	Black Bear Family Dental	1628 30th st NW	\N	Bemidji	MN	56601	US	(218) 444-2004	Veronica Cooper	Black Bear Family Dental	1628 30th st NW	\N	Bemidji	MN	56601	US	(218) 444-2004	fedex	556346	fedex_ground	FedEx Ground	\N
323	688345	2025-10-06	drmohs@yahoo.com	shipped	222405869	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Kahaja Mohsinuddin	Total Health Dental	2460 South Eola Road\nSuite H	\N	Aurora	IL	60503	US	(630) 585-5600	Kahaja Mohsinuddin	Total Health Dental	2460 South Eola Road\nSuite H	\N	Aurora	IL	60503	US	(630) 585-5600	fedex	556346	fedex_ground	FedEx Ground	\N
324	688355	2025-10-06	craighunterdarrington@gmail.com	shipped	222405872	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Craig Darrington	Sandcreek Dental	2460 E 25th St	\N	Idaho Falls	ID	83404	US	(208) 569-5680	Craig Darrington	Sandcreek Dental	2460 E 25th St	\N	Idaho Falls	ID	83404	US	(208) 569-5680	fedex	556346	fedex_ground	FedEx Ground	\N
347	688595	2025-10-06	info@matthewcripedds.com	shipped	222563678	2	0	ShipStation Manual	2025-10-06 20:30:26	2025-10-15 05:23:36.295358	\N	MATTHEW CRIPE	Dr. Matthew Cripe	303 Hamilton Street	\N	Dowagiac	MI	49047	US	2697825511	MATTHEW CRIPE	Dr. Matthew Cripe	303 Hamilton Street	\N	Dowagiac	MI	49047	US	2697825511	fedex	556346	fedex_ground	FedEx Ground	\N
325	688365	2025-10-06	hello@gracedentalfamily.com	shipped	222405876	7	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Misty Tecson	Grace Dental	90 middlefield rd\nSte 2	\N	menlo park	CA	94301	US	(650) 322-4750	Misty Tecson	Grace Dental	90 middlefield rd\nSte 2	\N	menlo park	CA	94301	US	(650) 322-4750	fedex	556346	fedex_ground	FedEx Ground	\N
326	688375	2025-10-06	karla@wilsondentistrytx.com	shipped	222405882	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Melissa Wilson	Wilson Dentistry	23020 Highland Knolls Blvd\nSuite B	\N	Katy	TX	77494	US	(346) 340-5440	Melissa Wilson	Wilson Dentistry	23020 Highland Knolls Blvd\nSuite B	\N	Katy	TX	77494	US	(346) 340-5440	fedex	556346	fedex_ground	FedEx Ground	\N
327	688385	2025-10-06	oxleyom21@gmail.com	shipped	222405886	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Eric Oxley	Oxley Comprehensive Dentistry	3004 trent Road	\N	New Bern	NC	28562	US	(252) 633-2500	Eric Oxley	Oxley Comprehensive Dentistry	3004 trent Road	\N	New Bern	NC	28562	US	(252) 633-2500	fedex	556346	fedex_ground	FedEx Ground	\N
328	688395	2025-10-06	frontoffice@tpdentistry.com	shipped	222405894	1	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Terrence Poole	Terrence S. Poole DDS	4605 E Galbraith Road\nSte 100	\N	Cincinnati	OH	45236	US	(513) 961-1991	Terrence Poole	Terrence S. Poole DDS	4605 E Galbraith Road\nSte 100	\N	Cincinnati	OH	45236	US	(513) 961-1991	fedex	556346	fedex_ground	FedEx Ground	\N
329	688405	2025-10-06	dralex@crystaldentalcenters.com	shipped	222406901	5	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Alexander Moradzadeh	Crystal Dental	2206 South Figueroa St	\N	los angeles	CA	90007	US	(310) 666-0378	Alexander Moradzadeh	Crystal Dental	2206 South Figueroa St	\N	los angeles	CA	90007	US	(310) 666-0378	fedex	556346	fedex_ground	FedEx Ground	\N
330	688415	2025-10-06	info@longislandsmile.com	shipped	222406908	3	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Neal Seltzer	Long Island Smile	101 Hillside Ave\nste A	\N	Williston Park	NY	11596	US	(516) 741-6202	Neal Seltzer	Long Island Smile	101 Hillside Ave\nste A	\N	Williston Park	NY	11596	US	(516) 741-6202	fedex	556346	fedex_ground	FedEx Ground	\N
331	688425	2025-10-06	supplies@zoedental.com	shipped	222406914	5	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Nikki Penland	Zoe Dental	10A Yorkshire St	\N	Ashville	NC	28803	US	(828) 274-1616	Nikki Penland	Zoe Dental	10A Yorkshire St	\N	Ashville	NC	28803	US	(828) 274-1616	fedex	556346	fedex_ground	FedEx Ground	\N
332	688435	2025-10-06	care@cozycabindental.com	shipped	222406921	5	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Dr Gardois	Cozy Cabin Dental	3755 W 7800 S	\N	West Jordan	UT	84088	US	(801) 871-5820	BILLING BILLING	BILLING	6116 S 2300 E	\N	Holladay	UT	84121	US	8018715820	fedex	556346	fedex_ground	FedEx Ground	\N
333	688445	2025-10-06	chandra@drchanwilliams.com	shipped	222406927	2	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Chandra Wiliams	Dr. Chandra Williams Family Dentistry	145 S Belair Rd	\N	Martinez	GA	30907	US	(706) 210-1519	Chandra Williams	Dr. Chandra Williams Family Dentistry	415 Amys Way	\N	Grovetown	GA	30813	US	7062101519	fedex	556346	fedex_ground	FedEx Ground	\N
334	688455	2025-10-06	wendy@oakhillsperiodontics.com	shipped	222406930	6	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Pamela Ray	Oakhills Periodontics	5419 Fredericksburg Road	\N	San Antonio	TX	78229	US	(210) 616-0980	Dawn Meseke	Oak Hill Perio	5830 Granite Parkway\nsuite 780	\N	Plano	TX	75024	US	14695966034	fedex	556346	fedex_ground	FedEx Ground	\N
335	688465	2025-10-06	villagedentist9@gmail.com	shipped	222406935	3	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	\N	Minh thu Tran	Village Dentist	2518 Tangley street	\N	houston	TX	77005	US	(713) 874-1500	Minh thu Tran	Village Dentist	2518 Tangley street	\N	houston	TX	77005	US	(713) 874-1500	fedex	556346	fedex_ground	FedEx Ground	\N
336	688475	2025-10-06	wendy@oakhillsperiodontics.com	shipped	222679060	10	0	ShipStation Manual	2025-10-06 15:14:21	2025-10-15 05:23:36.295358	20251007_065428_823004	Pamela Ray	Oakhills Periodontics	5419 Fredericksburg Road	\N	San Antonio	TX	78229	US	(210) 616-0980	Dawn Meseke	Oak Hill Perio	5830 Granite Parkway\nsuite 780	\N	Plano	TX	75024	US	14695966034	fedex	556346	fedex_ground	FedEx Ground	\N
355	100506	2025-10-06	antonio.diaz@pdshealth.com	shipped	222454310	6	0	ShipStation Manual	2025-10-07 06:12:18	2025-10-15 05:23:36.295358	\N	Oscar DeLeon	BANDERA MODERN DENTISTRY	9234 N LOOP 1604 W STE 121	\N	SAN ANTONIO	TX	78249-2984	US	(210) 681-1121	Oscar DeLeon	\N	\N	\N	\N	\N	\N	\N	(210) 681-1121	fedex	556346	fedex_ground	FedEx Ground	\N
337	688485	2025-10-06	office@concordadvanceddentistry.com	shipped	222459244	6	0	ShipStation Manual	2025-10-06 15:58:56	2025-10-15 05:23:36.295358	\N	Crystal Wilson	Concord Advanced Dentistry	3556 Concord Blvd suite D	\N	Concord	CA	94519	US	(925) 685-4820	Crystal Wilson	Concord Advanced Dentistry	244 West 54th Street\nSte 614	\N	New York	NY	10019	US	9256854820	fedex	556346	fedex_ground	FedEx Ground	\N
338	688495	2025-10-06	rosa.abreu@dentalnow14.com	shipped	222471649	15	0	ShipStation Manual	2025-10-06 16:39:10	2025-10-15 05:23:36.295358	\N	Shamim Cyrus	Dental Now 14	4141 Steve Reynolds Blvd\nSuite 1	\N	Norcross	GA	30093	US	9045548168	Shamim Cyrus	Dental Now 14	4141 Steve Reynolds Blvd\nSuite 1	\N	Norcross	GA	30093	US	9045548168	fedex	556346	fedex_ground	FedEx Ground	\N
339	688505	2025-10-06	info@glacialsandsoms.com	shipped	222489596	2	0	ShipStation Manual	2025-10-06 17:34:30	2025-10-15 05:23:36.295358	\N	Sonia Bennett	Glacial Sands oral, facial, implant surgery	1008 Broadway Ave	\N	Chesterton	IN	46304	US	(219) 964-4321	Sonia Bennett	Glacial Sands oral, facial, implant surgery	1008 Broadway Ave	\N	Chesterton	IN	46304	US	(219) 964-4321	fedex	556346	fedex_ground	FedEx Ground	\N
351	688525	2025-10-06	jami.markdilldds@gmail.com	shipped	222612813	40	0	ShipStation Manual	2025-10-06 23:21:12	2025-10-15 05:23:36.295358	\N	Jami Hollingsworth	Nooga Dentistry	6106 Shallowford Road\nSte 116	\N	Chattanooga	TN	37421	US	(423) 296-1053	Mark Dill	Nooga Dentistry	6550 Standifer Gap road	\N	Chattanooga	TN	37421	US	(423)296-1053	fedex	556346	fedex_ground	FedEx Ground	\N
608	690815	2025-10-15	the901dentist@gmail.com	shipped	\N	1	\N	X-Cart	2025-10-15 16:56:57.594205	2025-10-16 17:27:39.325556	\N	Elizabeth Mitchell	The 901 Dentist	795 Ridge Lake Blvd\nSuite 106	\N	Memphis	TN	38120	US	(901) 756-1151	Elizabeth Mitchell	The 901 Dentist	795 Ridge Lake Blvd\nSuite 106	\N	Memphis	TN	38120	US	(901) 756-1151	fedex	556346	fedex_ground	FedEx Ground	\N
343	688535	2025-10-06	info@dakotafamilysmiles.com	shipped	222542118	1	0	ShipStation Manual	2025-10-06 19:35:08	2025-10-15 05:23:36.295358	\N	Brock Oukrop	Dakota Family Smiles	4204 Boulder Ridge Rd Ste 140	\N	Bismarck	ND	58503	US	(701) 751-7300	Brock Oukrop	Dakota Family Smiles	3801 Horizon Place	\N	Bismark	ND	58503	US	701) 751-7300	fedex	556346	fedex_ground	FedEx Ground	\N
344	688545	2025-10-06	drbartkreiner@comcast.net	shipped	222543960	1	0	ShipStation Manual	2025-10-06 19:40:10	2025-10-15 05:23:36.295358	\N	D. BARTHOLOMEW KREINER	D. BARTHOLOMEW G. KREINER DDS, PA	511 S Fountain Green Rd	\N	Bel Air	MD	21015	US	(410) 459-8065	D. BARTHOLOMEW KREINER	D. BARTHOLOMEW G. KREINER DDS, PA	511 S Fountain Green Rd	\N	Bel Air	MD	21015	US	(410) 459-8065	fedex	556346	fedex_ground	FedEx Ground	\N
345	688555	2025-10-06	dumasorders@fullsmiledental.com	shipped	222559478	1	0	ShipStation Manual	2025-10-06 20:20:23	2025-10-15 05:23:36.295358	\N	Dr. Guzman	Full Smile Dental Dumas	315 E. 2nd Street	\N	Dumas	TX	79029	US	(806) 935-4161	Full Smile Management	Billing	2201 Civic Circle	\N	Amarillo	TX	79109	US	806-381-3435	fedex	556346	fedex_ground	FedEx Ground	\N
348	688605	2025-10-06	info@drbaird.com	shipped	222573284	15	0	ShipStation Manual	2025-10-06 21:00:35	2025-10-15 05:23:36.295358	\N	Aubrey Clark	Millcreek Family Dental	1509 S. Renaissance Towne Drive Suite 100	\N	Bountiful	UT	84010	US	(801) 888-0486	Aubrey Clark	Millcreek Family Dental	1509 S. Renaissance Towne Drive Suite 100	\N	Bountiful	UT	84010	US	(801) 888-0486	fedex	556346	fedex_ground	FedEx Ground	\N
349	688625	2025-10-06	drhurtte@gmail.com	shipped	222584759	6	0	ShipStation Manual	2025-10-06 21:40:46	2025-10-15 05:23:36.295358	\N	Eric Hurtte	Boardwalk Family Dental	7766 Winghaven Boulevard	\N	O FALLON	MO	63368	US	(636) 751-4602	Eric Hurtte	Boardwalk Family Dental	7766 Winghaven Boulevard	\N	O FALLON	MO	63368	US	(636) 751-4602	fedex	556346	fedex_ground	FedEx Ground	\N
350	688635	2025-10-06	doctor@priestriverdental.com	shipped	222586384	2	\N	X-Cart	2025-10-06 21:45:47	2025-10-15 05:23:36.295358	\N	Richard McKinney	Priest River Dental	6509 Hwy 2\nSte 102	\N	Priest River	ID	83856	US	(208) 448-2694	Richard McKinney	Priest River Dental	6509 Hwy 2\nSte 102	\N	Priest River	ID	83856	US	(208) 448-2694	fedex	556346	fedex_ground	FedEx Ground	\N
356	688645	2025-10-06	Lindsaycrossingdental@gmail.com	shipped	222689040	2	\N	X-Cart	2025-10-07 08:06:21	2025-10-15 05:23:36.295358	20251007_080957_114780	Sean Bringhurst	Lindsay Crossing Dental and Aesthetics	5505 S. Lindsay Rd. Ste. 106	\N	GILBERT	AZ	85298	US	(480) 351-3187	Sean Bringhurst	Lindsay Crossing Dental and Aesthetics	5505 S. Lindsay Rd. Ste. 106	\N	GILBERT	AZ	85298	US	(480) 351-3187	fedex	556346	fedex_ground	FedEx Ground	\N
357	688655	2025-10-07	dr.shenry@att.net	shipped	222705190	6	\N	X-Cart	2025-10-07 11:46:48	2025-10-15 05:23:36.295358	\N	Melissa Genova	Stephen R Henry DDS PC	58851 Van Dyke  suite 600	\N	Washington Twp	MI	48094	US	(586) 781-6700	Stephen Henry	Stephen Henry	3455 Nickelby	\N	Shelby Township	MI	48316	US	5867816700	fedex	556346	fedex_ground	FedEx Ground	\N
358	688665	2025-10-07	Saratoga@chauvindental.com	shipped	222705809	1	\N	X-Cart	2025-10-07 11:51:49	2025-10-15 05:23:36.295358	\N	Maian Vu	Chauvin Family Dentistry	403 Lake Ave	\N	Saratoga Springs	NY	12866	US	(518) 584-6302	Maian Vu	Chauvin Family Dentistry	403 Lake Ave	\N	Saratoga Springs	NY	12866	US	(518) 584-6302	fedex	556346	fedex_ground	FedEx Ground	\N
359	688685	2025-10-07	tn-alpinedentistry@hotmail.com	shipped	222744121	1	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Michael Trivis	Alpine dentistry	350 Broadway	\N	Boulder	CO	80305	US	(303) 494-8200	Michael Trivis	Alpine dentistry	350 Broadway	\N	Boulder	CO	80305	US	(303) 494-8200	fedex	556346	fedex_ground	FedEx Ground	\N
360	688695	2025-10-07	thomastippitdds@gmail.com	shipped	222782640	7	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Thomas Tippit	Thomas Tippit DDS	4501 S Staples Street	\N	Corpus Christi	TX	78411	US	(361) 992-8071	Thomas Tippit	Thomas Tippit DDS	4501 S Staples Street	\N	Corpus Christi	TX	78411	US	(361) 992-8071	fedex	556346	fedex_ground	FedEx Ground	\N
361	688705	2025-10-07	nwassistants@gmail.com	shipped	222782542	2	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Laura Holderness	Nathan Wong Digital Dentistry	881 pacific street	\N	san luis obispo	CA	93401	US	(805) 543-6535	Laura Holderness	Nathan Wong Digital Dentistry	881 pacific street	\N	san luis obispo	CA	93401	US	(805) 543-6535	fedex	556346	fedex_ground	FedEx Ground	\N
362	688715	2025-10-07	gunnellfamilydentistry@gmail.com	shipped	222758611	1	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Clayton Gunnell	Gunnell Family Dentistry	1320 N 600 E\nSte 2	\N	Logan	UT	84341	US	(435) 752-1747	Clayton Gunnell	Gunnell Family Dentistry	1320 N 600 E\nSte 2	\N	Logan	UT	84341	US	(435) 752-1747	fedex	556346	fedex_ground	FedEx Ground	\N
363	688725	2025-10-07	aaronmanosdds@gmail.com	shipped	222761946	2	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Aaron Manos	Aaron Manos DDS PLLC	8650 Babcock Blvd\nSuite 3	\N	Pittsburgh	PA	15237	US	(412) 367-4515	Aaron Manos	Aaron Manos DDS PLLC	8650 Babcock Blvd\nSuite 3	\N	Pittsburgh	PA	15237	US	(412) 367-4515	fedex	556346	fedex_ground	FedEx Ground	\N
364	688735	2025-10-07	judymejido@gmail.com	shipped	222782608	16	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Judy Mejido	Judy Mejido DMD PA- TB	9560 SW 107th Ave  Suite 206	\N	Miami	FL	33176	US	(305) 274-2110	Judy Mejido	Judy Mejido DMD PA- TB	9560 SW 107th Ave  Suite 206	\N	Miami	FL	33176	US	(305) 274-2110	fedex	556346	fedex_ground	FedEx Ground	\N
365	688745	2025-10-07	office@davidlkresedds.com	shipped	222788648	1	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	David Krese	David L Krese, D.D.S.	240 Hydraulic Ridge Road\nSte 201	\N	Charlottesville	VA	22901	US	(434) 971-8159	David Krese	David L Krese, D.D.S.	240 Hydraulic Ridge Road\nSte 201	\N	Charlottesville	VA	22901	US	(434) 971-8159	fedex	556346	fedex_ground	FedEx Ground	\N
366	688755	2025-10-07	northwoodsdentalspa@yahoo.com	shipped	222794471	6	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Irene Blaess	Northwoods Dental Spa	18160 hwy 281 north suite 104	\N	San Antonio	TX	78232	US	(210) 495-7800	Irene Blaess	Northwoods Dental Spa	18160 hwy 281 north suite 104	\N	San Antonio	TX	78232	US	(210) 495-7800	fedex	556346	fedex_ground	FedEx Ground	\N
367	688765	2025-10-07	riverwestdental@gmail.com	shipped	222803848	1	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Chandler Bell	RiverWest Dental	1655 Pancheri Dr.	\N	Idaho Falls	ID	83402	US	(208) 522-1911	Chandler Bell	RiverWest Dental	1655 Pancheri Dr.	\N	Idaho Falls	ID	83402	US	(208) 522-1911	fedex	556346	fedex_ground	FedEx Ground	\N
368	688785	2025-10-07	office@bperio.com	shipped	222809455	6	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Thomas Bodnar	Bodnar Periodontics	21851 Center Ridge Road Suite #104	\N	Rocky River	OH	44116	US	(440) 331-3044	Thomas Bodnar	Bodnar Periodontics	4354 Valley Forge Drive	\N	Fairview Park	OH	44126	US	4403313044	fedex	556346	fedex_ground	FedEx Ground	\N
369	688795	2025-10-07	shelby@wilmarmanagement.com	shipped	222809458	48	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Robert Martino	Wilmar Management	2000 Industrial Road East\nSuite 200	\N	Bridgeport	WV	26330	US	3049335300	Robert Martino	Wilmar Management	2000 Industrial Road East\nSuite 200	\N	Bridgeport	WV	26330	US	3049335300	fedex	556346	fedex_ground	FedEx Ground	\N
370	688805	2025-10-07	Smiles2@officedds.com	shipped	222821614	6	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Sandra Miles	Miles and Michael Dentistry	2802 Market Street	\N	Wilmington	NC	28403	US	(910) 815-0811	Sandra Miles	Miles and Michael Dentistry	2802 Market Street	\N	Wilmington	NC	28403	US	(910) 815-0811	fedex	556346	fedex_ground	FedEx Ground	\N
371	688815	2025-10-07	info@HDhayward.com	shipped	222821615	1	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Virna Villas	Highland Dental of Hayward	1372 A Street	\N	Hayward	CA	94541	US	(510) 314-0765	Virna Villas	Highland Dental of Hayward	1372 A Street	\N	Hayward	CA	94541	US	(510) 314-0765	fedex	556346	fedex_ground	FedEx Ground	\N
372	688825	2025-10-07	dahdentistry@hotmail.com	shipped	222828059	1	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	David Horn	DAH Dentistry	1515 SE Luckhardt St.	\N	Stuart	FL	34994	US	(772) 781-0835	David Horn	DAH Dentistry	5607 SW Moore St	\N	palm city	FL	34990	US	7722860925	fedex	556346	fedex_ground	FedEx Ground	\N
373	688835	2025-10-07	office@baycolonydentistry.com	shipped	222836095	7	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Debra Blanchard	Bay Colony Dentistry	3102 Holly Rd\nSte 506	\N	Virginia Beach	VA	23451	US	(757) 321-1300	Debra Blanchard	Bay Colony Dentistry	3102 Holly Rd\nSte 506	\N	Virginia Beach	VA	23451	US	(757) 321-1300	fedex	556346	fedex_ground	FedEx Ground	\N
374	688845	2025-10-07	doced22@gmail.com	shipped	222838734	1	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Ed Stephens	Dr Ed Stephens	1109 Omar Street	\N	Mexico	MO	65265	US	(573) 581-1054	Ed Stephens	Dr Ed Stephens	1109 Omar Street	\N	Mexico	MO	65265	US	(573) 581-1054	fedex	556346	fedex_ground	FedEx Ground	\N
375	688855	2025-10-07	drmalterud@gmail.com	shipped	222840204	1	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Mark Malterud	Mark I Malterud DDS PA	770 Mount Curve Blvd	\N	St. Paul	MN	55116	US	(651) 699-2822	Mark Malterud	Mark I Malterud DDS PA	770 Mount Curve Blvd	\N	St. Paul	MN	55116	US	(651) 699-2822	fedex	556346	fedex_ground	FedEx Ground	\N
376	688865	2025-10-07	northmaindental@yahoo.com	shipped	222840207	2	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Paul Ponte	North Main Dental Associates- Fall River	1120 N Main Street	\N	Fall River	MA	02720	US	(508) 674-8811	Paul Ponte	North Main Dental Associates- Fall River	1120 N Main Street	\N	Fall River	MA	02720	US	(508) 674-8811	fedex	556346	fedex_ground	FedEx Ground	\N
377	688875	2025-10-07	chad@tncld.com	shipped	222850238	5	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Chad Edwards	Tennessee Centers for Laser Dentistry	204 Miller Springs Court\nSte 200	\N	Franklin	TN	37064	US	615-595-8070	Chad Edwards	Tennessee Centers for Laser Dentistry	3046 Columbia Ave\nSuite 201	\N	Franklin	TN	37064	US	(615) 595-8070	fedex	556346	fedex_ground	FedEx Ground	\N
378	688885	2025-10-07	hygienists@kcsmile.com	shipped	222859716	1	\N	X-Cart	2025-10-07 21:29:37	2025-10-15 05:23:36.295358	\N	Ross Headley	KC Smile	12850 Metcalf\nSuite 200	\N	Overland Park	KS	66213	US	(913) 491-6874	Ross Headley	KC Smile	12850 Metcalf\nSuite 200	\N	Overland Park	KS	66213	US	(913) 491-6874	fedex	556346	fedex_ground	FedEx Ground	\N
380	688895	2025-10-07	Rivergatevillagedental@gmail.com	shipped	222870004	1	\N	X-Cart	2025-10-07 21:59:46	2025-10-15 05:23:36.295358	20251007_220040_401874	Angel Hall	Rivergate Village Dental	1570 Gallatin Pike North	\N	Madison	TN	37115	US	16153378619	Angel Hall	Rivergate Village Dental	1570 Gallatin Pike North	\N	Madison	TN	37115	US	16153378619	fedex	556346	fedex_ground	FedEx Ground	\N
381	688905	2025-10-08	office@riversidedental-co.com	shipped	222988025	6	\N	X-Cart	2025-10-08 12:28:41	2025-10-15 05:23:36.295358	\N	Mollie Richardson	Riverside Dental	2630 W BELLEVIEW AVE STE 260\nSUITE 260	\N	Littleton	CO	80123	US	(720) 524-3854	Mollie Richardson	Riverside Dental	2630 W BELLEVIEW AVE STE 260\nSUITE 260	\N	Littleton	CO	80123	US	(720) 524-3854	fedex	556346	fedex_ground	FedEx Ground	\N
382	688915	2025-10-08	hlipscomb@jonquildental.com	on_hold	222991444	2	\N	X-Cart	2025-10-08 15:30:51	2025-10-15 05:23:36.295358	\N	Heather Lipscomb	Jonquil Family Dental	4933 Jonquil Drive	\N	Nashville,TN	TN	37211	US	(615) 834-6363	Heather Lipscomb	Jonquil Family Dental	4933 Jonquil Drive	\N	Nashville,TN	TN	37211	US	(615) 834-6363	fedex	556346	fedex_ground	FedEx Ground	\N
383	688925	2025-10-08	cooneyfamilydental@gmail.com	shipped	223006443	2	\N	X-Cart	2025-10-08 15:30:51	2025-10-15 05:23:36.295358	\N	Nathan Cooney	Cooney Family Dental	1792 W 1700 S, #203	\N	Syracuse	UT	84075	US	(801) 779-6037	Nathan Cooney	Cooney Family Dental	921 S 2200 W	\N	Syracuse	UT	84075	US	8017796037	fedex	556346	fedex_ground	FedEx Ground	\N
384	688945	2025-10-08	BPFD@yahoo.com	shipped	223013701	6	\N	X-Cart	2025-10-08 15:30:51	2025-10-15 05:23:36.295358	\N	Alexandria Gibbs	Bandera Pointe Family Dental	11309 Bandera Rd\nSte 101	\N	San Antonio	TX	78250	US	(210) 776-7266	Alexandria Gibbs	Bandera Pointe Family Dental	11309 Bandera Rd\nSte 101	\N	San Antonio	TX	78250	US	(210) 776-7266	fedex	556346	fedex_ground	FedEx Ground	\N
385	688955	2025-10-08	office@leahzilsdds.com	shipped	223014738	1	\N	X-Cart	2025-10-08 15:30:51	2025-10-15 05:23:36.295358	\N	Leah Zils	Leah Zils DDS	6769 Lake Woodlands Dr. Suite A	\N	The Woodlands	TX	77382	US	(281) 681-9442	Leah Zils	Leah Zils DDS	6769 Lake Woodlands Dr. Suite A	\N	The Woodlands	TX	77382	US	(281) 681-9442	fedex	556346	fedex_ground	FedEx Ground	\N
386	688965	2025-10-08	glenrose@polishedfamilydental.com	shipped	223021465	6	\N	X-Cart	2025-10-08 15:30:51	2025-10-15 05:23:36.295358	\N	Amber Powell	Polished Family Dental - Glen Rose	104 Spanish Oak Trail	\N	GLEN ROSE	TX	76043	US	(254) 897-3143	Clayton Cook	Polished Family Dental - Glen Rose	104 Spanish Oak Trail	\N	GLEN ROSE	TX	76028	US	(254) 897-3143	fedex	556346	fedex_ground	FedEx Ground	\N
387	688975	2025-10-08	newtonsmilecentre@gmail.com	shipped	223023369	6	\N	X-Cart	2025-10-08 15:30:51	2025-10-15 05:23:36.295358	\N	Walid Benaissa	Newton Smile Centre	796 Beacon St	\N	Newton	MA	02459	US	(617) 928-9299	Walid Benaissa	Newton Smile Centre	796 Beacon St	\N	Newton	MA	02459	US	(617) 928-9299	fedex	556346	fedex_ground	FedEx Ground	\N
388	688985	2025-10-08	cambrestephen@bellsouth.net	shipped	223032621	1	\N	X-Cart	2025-10-08 15:30:51	2025-10-15 05:23:36.295358	\N	Stephen Cambre	Stephen M Cambre DDS	315 Rober BLVD\nSTE B	\N	Slidell	LA	70458	US	(985) 643-2284	Stephen Cambre	Stephen M Cambre DDS	315 Rober BLVD\nSTE B	\N	Slidell	LA	70458	US	(985) 643-2284	fedex	556346	fedex_ground	FedEx Ground	\N
389	688995	2025-10-08	info@draarondental.com	shipped	223038626	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Nicole Schaefer	Angela Aaron DDS	20 Franklin turnpike Suite 210	\N	Waldwick	NJ	07463	US	(201) 857-2842	Nicole Schaefer	Angela Aaron DDS	20 Franklin turnpike Suite 210	\N	Waldwick	NJ	07463	US	(201) 857-2842	fedex	556346	fedex_ground	FedEx Ground	\N
390	689015	2025-10-08	Office@smilemaryville.com	shipped	223038631	15	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Jonathan Mitchell	MARYVILLE FAMILY DENTISTRY	11302 Preston Highway	\N	Louisville	KY	40229	US	(502) 955-6134	Jonathan Mitchell	MARYVILLE FAMILY DENTISTRY	11302 Preston Highway	\N	Louisville	KY	40229	US	(502) 955-6134	fedex	556346	fedex_ground	FedEx Ground	\N
391	689025	2025-10-08	mariaserranodds@gmail.com	shipped	223040689	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Maria Serrano	Alma Dental Care	131 Lynch Creek Way, Suite C	\N	Petaluma	CA	94954	US	(707-762-6645	Maria Serrano	Alma Dental Care	131 Lynch Creek Way, Suite C	\N	Petaluma	CA	94954	US	(707-762-6645	fedex	556346	fedex_ground	FedEx Ground	\N
392	689035	2025-10-08	info@blossomdentalwellness.com	shipped	223040692	6	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Novan Nguyen	blossom dental wellness	7600 Green Haven Dr\nSte 301	\N	Sacramento	CA	95831	US	(916) 422-3991	novan nguyen	novan dental	10066 Dona Neely Way	\N	elk grove	CA	95757	US	+919164223991	fedex	556346	fedex_ground	FedEx Ground	\N
393	689045	2025-10-08	dr_hedrick@att.net	shipped	223044564	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Darrell Hedrick	Darrell W Hedrick DDS LLC	2001 Laquesta Drive	\N	Neosho	MO	64850	US	(417) 451-3545	Darrell Hedrick	Darrell W Hedrick DDS LLC	2001 Laquesta Drive	\N	Neosho	MO	64850	US	(417) 451-3545	fedex	556346	fedex_ground	FedEx Ground	\N
394	689055	2025-10-08	office@warefamilydentistry.com	shipped	223049395	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Jenee Ware	Ware Family Dentistry	637 17th St	\N	Vero Beach	FL	32960	US	(772) 567-2111	Jenee Ware	Ware Family Dentistry	637 17th St	\N	Vero Beach	FL	32960	US	(772) 567-2111	fedex	556346	fedex_ground	FedEx Ground	\N
402	689145	2025-10-08	generationsparma@forestdp.com	shipped	223105001	6	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Holly Waite	Generations Dental Care	1440 Rockside Rd\nSte 212	\N	Parma	OH	44134	US	(216) 749-1242	Holly Waite	Generations Dental Care	1440 Rockside Rd\nSte 212	\N	Parma	OH	44134	US	(216) 749-1242	fedex	556346	fedex_ground	FedEx Ground	\N
403	689155	2025-10-08	leadedda.rmdp@gmail.com	shipped	223108608	2	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Kyle Ricks	Aurora Family Dentistry	13700 E Colfax Ave\nSuite M	\N	Aurora	CO	80011	US	(303) 364-4322	Kyle Ricks	Aurora Family Dentistry	13700 E Colfax Ave\nSuite M	\N	Aurora	CO	80011	US	(303) 364-4322	fedex	556346	fedex_ground	FedEx Ground	\N
404	689165	2025-10-08	canesdds@att.net	shipped	223134282	6	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Dr. Leyte- Marco	Sunset Dentistry	6280 Sunset Drive\nSuite 404	\N	South Miami	FL	33143	US	(305) 661-7810	Marco Leyte Marco Leyte	Sunset Dentisry	7420 South West 166 st	\N	Palmetto Bay	FL	33157	US	(305) 661-7810	fedex	556346	fedex_ground	FedEx Ground	\N
405	689175	2025-10-08	yfd@yfdentistry.com	shipped	223134287	3	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Christopher Lim	Yellowstone Family Dentistry	110 Yellowstone Dr. Suite 100	\N	Chico	CA	95973	US	(530) 895-3449	Christopher Lim	Yellowstone Family Dentistry	110 Yellowstone Dr. Suite 100	\N	Chico	CA	95973	US	(530) 895-3449	fedex	556346	fedex_ground	FedEx Ground	\N
406	689185	2025-10-08	claritydentalllc@gmail.com	shipped	223149407	6	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Ramla Ahmed	Clarity Dental	4C Auer Ct	\N	East Brunswick	NJ	08816	US	(732) 254-6669	Ramla Ahmed	Clarity Dental	4C Auer Ct	\N	East Brunswick	NJ	08816	US	(732) 254-6669	fedex	556346	fedex_ground	FedEx Ground	\N
407	689195	2025-10-08	info@newportdentalgroup.com	shipped	223165607	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 05:23:36.295358	\N	Sean Saghatchi	Newport Dental Group	1835 Newport Blvd. Suite E267	\N	Costa Mesa	CA	92627	US	(949) 574-0100	Sean Saghatchi	Newport Dental Group	1835 Newport Blvd. Suite E267	\N	Costa Mesa	CA	92627	US	(949) 574-0100	fedex	556346	fedex_ground	FedEx Ground	\N
428	100513	2025-10-09		shipped	223286829	15	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Robert Krantz	NEW BRAUNFELS MODERN DENTISTRY	244 FM 306 STE 118	\N	NEW BRAUNFELS	TX	78130-5487	US	\N	Robert Krantz	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_ground	FedEx Ground	\N
429	100514	2025-10-09	carpenteresteydds@yahoo.com	shipped	223313392	2	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Erin Estey	ESTEY & CARPENTER DENTISTRY	1806 ORANGE TREE LN STE B	\N	REDLANDS	CA	92374-4574	US	(909) 335-1166	Erin Estey	\N	\N	\N	\N	\N	\N	\N	(909) 335-1166	fedex	556346	fedex_ground	FedEx Ground	\N
430	100515	2025-10-09	cb9540@benco.com	shipped	223362625	10	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Courtney Brahm	BENCO DENTAL COMPANY BC	295 CENTERPOINT BLVD	\N	PITTSTON	PA	18640-6136	US	8552556722	Courtney Brahm	\N	\N	\N	\N	\N	\N	\N	8552556722	fedex	560734	fedex_ground	FedEx Ground	\N
431	100516	2025-10-09	cb9540@benco.com	shipped	223363554	8	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Courtney Brahm	BENCO DENTAL COMPANY JAX	13525 INTERNATIONAL PKWY	\N	JACKSONVILLE	FL	32218-9447	US	8552556722	Courtney Brahm	\N	\N	\N	\N	\N	\N	\N	8552556722	fedex	560734	fedex_ground	FedEx Ground	\N
432	100517	2025-10-09	cb9540@benco.com	shipped	223364508	6	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Courtney Brahm	BENCO DENTAL COMPANY RENO	625 WALTHAM WAY STE 107	\N	SPARKS	NV	89437-9592	US	8552556722	Courtney Brahm	\N	\N	\N	\N	\N	\N	\N	8552556722	fedex	560734	fedex_ground	FedEx Ground	\N
416	689315	2025-10-09	Cockrelldental@yahoo.com	shipped	223298511	1	\N	X-Cart	2025-10-09 20:46:14	2025-10-15 14:44:57.572796	\N	Kevin Cockrell	Cockrell Dental Office	1040 Hillcrest Rd	\N	Mobile	AL	36695	US	(251) 639-0110	Kevin Cockrell	Cockrell Dental Office	1040 Hillcrest Rd	\N	Mobile	AL	36695	US	(251) 639-0110	fedex	556346	fedex_ground	FedEx Ground	\N
435	100520	2025-10-09	carpenteresteydds@yahoo.com	shipped	223387853	2	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Erin Estey	ESTEY & CARPENTER DENTISTRY	1806 ORANGE TREE LN STE B	\N	REDLANDS	CA	92374-4574	US	(909) 335-1166	Erin Estey	\N	1806 Orange Tree Lane	\N	Redlands	CA	92374	US	\N	fedex	556346	fedex_2day	FedEx 2Day	\N
445	689475	2025-10-10	Info@philipshindlerdds.com	shipped	223772351	2	\N	X-Cart	2025-10-10 20:15:39	2025-10-16 17:11:42.473262	\N	Philip Shindler	Agoura Hill Family and Cosmetic Dentistry	30200 Agoura Rd\n#180	\N	Agoura Hills	CA	91301	US	(805) 495-0187	Philip Shindler	Agoura Hill Family and Cosmetic Dentistry	30200 Agoura Rd\n#180	\N	Agoura Hills	CA	91301	US	(805) 495-0187	fedex	556346	fedex_ground	FedEx Ground	\N
442	689435	2025-10-09	Drpinto@drchelseapinto.com	shipped	223461521	2	\N	X-Cart	2025-10-10 00:37:27	2025-10-15 23:09:48.164681	\N	Chelsea Pinto	Chelsea Pinto DDS	6059 Canterbury Dr	\N	Agoura Hills	CA	91364	US	(317) 440-5940	Chelsea Pinto	Chelsea Pinto DDS	20301 Ventura Blvd. #110	\N	Woodland Hills	CA	91364	US	(317) 440-5940	fedex	556346	fedex_ground	FedEx Ground	\N
441	689425	2025-10-09	rspsr@yahoo.com	shipped	223432822	1	\N	X-Cart	2025-10-09 21:21:24	2025-10-15 21:11:11.117842	20251009_212227_489393	Ricahard S Powell	Auburn Renewal Center	12225 Rock Creek Rd	\N	Auburn	CA	95602	US	(530) 320-6717	Ricahard S Powell	Auburn Renewal Center	12225 Rock Creek Rd	\N	Auburn	CA	95602	US	(530) 320-6717	fedex	556346	fedex_ground	FedEx Ground	\N
444	689465	2025-10-10	changing.smiles1@yahoo.com	shipped	223704305	1	\N	X-Cart	2025-10-10 14:31:24	2025-10-16 14:12:52.371646	\N	Wendy Piero	Greggory Elefterin DDS	4774 Munson St NW\nSuite #201	\N	Canton	OH	44718	US	(330) 494-3133	Wendy Piero	Greggory Elefterin DDS	4774 Munson St NW\nSuite #201	\N	Canton	OH	44718	US	(330) 494-3133	fedex	556346	fedex_ground	FedEx Ground	\N
439	689405	2025-10-09	mikkah@oracareproducts.com	shipped	223429545	4	\N	X-Cart	2025-10-09 21:06:20	2025-10-15 18:06:26.449834	20251009_210721_483365	Devon Berry	The Art of Dentistry-TruBlu	32 World's Fair Drive	\N	Somerset	NJ	08873	US	(732) 846-7100	Billing Billing	Billing	3333 New Hyde Park Road\nSte304	\N	New Hyde Park	NM	11042	US	516-344-5746	fedex	556346	fedex_ground	FedEx Ground	\N
440	689415	2025-10-09	drobrien@travelingdentistofnj.com	shipped	223429548	1	\N	X-Cart	2025-10-09 21:06:20	2025-10-15 18:06:26.449834	20251009_210721_483365	Arlene O'Brien	Traveling Dentist of New Jersey	10 Douglass Dr	\N	Princeton	NJ	08540	US	(908) 242-6223	Arlene O'Brien	Traveling Dentist of New Jersey	P.O. Box 308	\N	Kingston	NJ	08528	US	(908) 242-6223	fedex	556346	fedex_ground	FedEx Ground	\N
443	689455	2025-10-10	lab@titensordental.com	shipped	223692299	6	\N	X-Cart	2025-10-10 13:41:08	2025-10-16 13:34:35.986941	\N	Brett Titensor	Titensor Dental	1901 Long Prairie Road\nSuite 320	\N	Flower Mound	TX	75022	US	(972) 355-9545	Brett Titensor	Titensor Dental	1901 Long Prairie Road\nSuite 320	\N	Flower Mound	TX	75022	US	(972) 355-9545	fedex	556346	fedex_ground	FedEx Ground	\N
433	100518	2025-10-09		cancelled	223689910	1	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Kaye Dentistry	\N	455 CENTRAL PARK AVE STE 315	\N	SCARSDALE	NY	10583-1034	US	\N	Kaye Dentistry	\N	\N	\N	\N	\N	\N	\N	\N	fedex	556346	fedex_2day	FedEx 2Day	\N
434	100519	2025-10-09	ravikumarr@pacden.com	cancelled	223724754	2	0	ShipStation Manual	2025-10-09 20:49:12	2025-10-15 05:23:36.295358	\N	Rakshith Arakotaram Ravikumar	BASTROP MODERN DENTISTRY	1670 HIGHWAY 71 E STE A	\N	BASTROP	TX	78602-2034	US	512-240-6496	Rakshith Arakotaram Ravikumar	\N	\N	\N	\N	\N	\N	\N	512-240-6496	fedex	556346	fedex_ground	FedEx Ground	\N
451	689515	2025-10-10	hygiene@prosperfamilydentistry.com	shipped	224358258	8	\N	X-Cart	2025-10-13 16:02:29	2025-10-16 17:27:39.325556	\N	Jill Sentlingar	Prosper Family Dentistry	201 N Preston Road	\N	Prosper	TX	75078	US	(972) 347-1145	Jill Sentlingar	Prosper Family Dentistry	201 N Preston Road	\N	Prosper	TX	75078	US	(972) 347-1145	fedex	556346	fedex_2day	FedEx 2Day	\N
468	689695	2025-10-13	Ezdentalcare1@gmail.com	shipped	224458669	6	\N	X-Cart	2025-10-13 19:49:07	2025-10-16 17:27:39.325556	\N	Deeksha Taneia	EZ Dental Care LLC	775 Hungerfold Drive	\N	Rockville	MD	20850	US	(301) 545-1666	Deeksha Taneia	EZ Dental Care LLC	775 Hungerfold Drive	\N	Rockville	MD	20850	US	(301) 545-1666	fedex	556346	fedex_ground	FedEx Ground	\N
495	690045	2025-10-14	robert.nakisher@gmail.com	shipped	\N	40	\N	X-Cart	2025-10-14 19:00:20	2025-10-16 17:27:39.325556	\N	Robert Nakisher	Lakeview Family Dental	7010 Pontiac trail	\N	West Bloomfield	MI	48323	US	(248) 363-3304	Robert Nakisher	Lakeview Family Dental	7010 Pontiac trail	\N	West Bloomfield	MI	48323	US	(248) 363-3304	fedex	556346	fedex_ground	FedEx Ground	\N
496	690055	2025-10-14	nwendopc@gmail.com	shipped	\N	7	\N	X-Cart	2025-10-14 19:35:31	2025-10-16 17:27:39.325556	\N	Brittney Penberthy	Northwest Endodontics	509 W. Hanley Ave\nSuite 202	\N	Coeur d'Alene	ID	83815	US	(208) 667-8622	Brittney Penberthy	Northwest Endo	17770 W Bison Trail	\N	Post Falls	ID	83854	US	2086678622	fedex	556346	fedex_ground	FedEx Ground	\N
497	690075	2025-10-14	office@benromenesko.dental	shipped	\N	2	\N	X-Cart	2025-10-14 20:15:43	2025-10-16 17:27:39.325556	\N	DeDe Parker	Romenesko Family Dentistry	2510 E Evergreen Dr	\N	Appleton	WI	54913	US	(920) 739-6173	DeDe Parker	Romenesko Family Dentistry	2510 E Evergreen Dr	\N	Appleton	WI	54913	US	(920) 739-6173	fedex	556346	fedex_ground	FedEx Ground	\N
498	690085	2025-10-14	drphil@pracmedsolutions.com	shipped	\N	1	\N	X-Cart	2025-10-14 20:25:47	2025-10-16 17:27:39.325556	\N	Phil Roberts	Prac Med Solutions	1239 Broadmoor Cir	\N	Franklin	TN	37067	US	(615) 948-1200	Phil Roberts	Prac Med Solutions	1239 Broadmoor Cir	\N	Franklin	TN	37067	US	(615) 948-1200	fedex	556346	fedex_ground	FedEx Ground	\N
499	690115	2025-10-14	info@alliancefamilydentistry.com	shipped	\N	2	\N	X-Cart	2025-10-14 20:50:55	2025-10-16 17:27:39.325556	\N	Aimee Wilson	Alliance Family Dentistry	6140 Tutt Blvd\nSuite #150	\N	Colorado Springs	CO	80923	US	(719) 955-4023	Aimee Wilson	Alliance Family Dentistry	6140 Tutt Blvd\nSuite #150	\N	Colorado Springs	CO	80923	US	(719) 955-4023	fedex	556346	fedex_ground	FedEx Ground	\N
500	690135	2025-10-14	birchfamilydentistrywy@gmail.com	shipped	\N	6	\N	X-Cart	2025-10-14 21:26:06	2025-10-16 17:27:39.325556	\N	Charity Clark	Birch Family Dentistry	661 Uinta Drive	\N	Green River	WY	82935	US	(307) 875-3658	Charity Clark	Birch Family Dentistry	661 Uinta Drive	\N	Green River	WY	82935	US	(307) 875-3658	fedex	556346	fedex_ground	FedEx Ground	\N
501	690145	2025-10-14	kasnerdds@gmail.com	shipped	\N	6	\N	X-Cart	2025-10-14 21:56:17	2025-10-16 17:27:39.325556	\N	Darcy kasner	Artisan Dentistry	3318 J st	\N	Sacramento	CA	95816	US	(916) 452-2002	Darcy kasner	Artisan Dentistry	3318 J st	\N	Sacramento	CA	95816	US	(916) 452-2002	fedex	556346	fedex_ground	FedEx Ground	\N
502	690155	2025-10-14	infoHCFDental@gmail.com	shipped	\N	1	\N	X-Cart	2025-10-14 22:16:22	2025-10-16 17:27:39.325556	\N	Lacy Jones	Hunt Club Family Dental	1509 Hunt Club Blvd\nSte 800	\N	Gallatin	TN	37066	US	(615) 452-6765	Lacy Jones	Hunt Club Family Dental	1509 Hunt Club Blvd\nSte 800	\N	Gallatin	TN	37066	US	(615) 452-6765	fedex	556346	fedex_ground	FedEx Ground	\N
490	689975	2025-10-14	ghaas1949@gmail.com	shipped	224764398	2	\N	X-Cart	2025-10-14 16:09:24	2025-10-16 17:27:39.325556	\N	Galen Haas	Fairview Dental	1639 23rd Av.	\N	Lewiston	ID	83501	US	(208) 746-0431	Galen Haas	Fairview Dental	1639 23rd Av.	\N	Lewiston	ID	83501	US	(208) 746-0431	fedex	556346	fedex_ground	FedEx Ground	\N
494	690035	2025-10-14	info@musiccitydental.com	shipped	\N	1	\N	X-Cart	2025-10-14 18:40:12	2025-10-16 17:27:39.325556	\N	Terry Spurlin'Moore	Music City Dental	808 Kirkwood Avenue	\N	Nashville	TN	37204	US	(615) 953-2469	Terry Spurlin'Moore	Music City Dental	808 Kirkwood Avenue	\N	Nashville	TN	37204	US	(615) 953-2469	fedex	556346	fedex_ground	FedEx Ground	\N
\.


--
-- Data for Name: shipped_items; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.shipped_items (id, ship_date, sku_lot, base_sku, quantity_shipped, order_number, created_at, tracking_number) FROM stdin;
849	2025-08-22	17612 - 250216	17612	2	678565	2025-10-01 19:32:37	\N
850	2025-08-22	17612 - 250216	17612	6	678655	2025-10-01 19:32:37	\N
851	2025-08-22	17904 - 240276	17904	1	678665	2025-10-01 19:32:37	\N
852	2025-08-22	17612 - 250216	17612	6	678615	2025-10-01 19:32:37	\N
853	2025-08-22	17914 - 240286	17914	6	678635	2025-10-01 19:32:37	\N
854	2025-08-22	17612 - 250216	17612	2	678645	2025-10-01 19:32:37	\N
855	2025-08-22	17612 - 250216	17612	8	675975	2025-10-01 19:32:37	\N
856	2025-08-22	17612 - 250216	17612	6	678635	2025-10-01 19:32:37	\N
857	2025-08-22	17612 - 250216	17612	1	678605	2025-10-01 19:32:37	\N
858	2025-08-22	17612 - 250216	17612	3	674715	2025-10-01 19:32:37	\N
859	2025-08-22	18675 - 240231	18675	1	678635	2025-10-01 19:32:37	\N
860	2025-08-22	17612 - 250216	17612	6	678595	2025-10-01 19:32:37	\N
861	2025-08-22	17612 - 250216	17612	1	678585	2025-10-01 19:32:37	\N
863	2025-08-22	17612 - 250216	17612	2	678575	2025-10-01 19:32:37	\N
864	2025-08-22	17612 - 250216	17612	2	673125	2025-10-01 19:32:37	\N
865	2025-08-22	17612 - 250216	17612	1	678625	2025-10-01 19:32:37	\N
866	2025-08-22	17914 - 240286	17914	1	671825	2025-10-01 19:32:37	\N
867	2025-08-22	17612 - 250216	17612	1	678665	2025-10-01 19:32:37	\N
868	2025-08-22	17612 - 250216	17612	1	675355	2025-10-01 19:32:37	\N
869	2025-08-25	17612 - 250216	17612	1	100462	2025-10-01 19:32:37	\N
870	2025-08-25	17612 - 250216	17612	1	678915	2025-10-01 19:32:37	\N
871	2025-08-25	17612 - 250216	17612	20	678895	2025-10-01 19:32:37	\N
872	2025-08-25	17914 - 240286	17914	1	100463	2025-10-01 19:32:37	\N
873	2025-08-25	17612 - 250216	17612	4	678885	2025-10-01 19:32:37	\N
874	2025-08-25	17612 - 250216	17612	6	679125	2025-10-01 19:32:37	\N
875	2025-08-25	17612 - 250216	17612	6	679055	2025-10-01 19:32:37	\N
876	2025-08-25	17914 - 240286	17914	2	678985	2025-10-01 19:32:37	\N
877	2025-08-25	17612 - 250216	17612	2	679115	2025-10-01 19:32:37	\N
878	2025-08-25	17612 - 250216	17612	2	678735	2025-10-01 19:32:37	\N
879	2025-08-25	17612 - 250216	17612	6	679045	2025-10-01 19:32:37	\N
880	2025-08-25	17612 - 250216	17612	2	678835	2025-10-01 19:32:37	\N
881	2025-08-25	17612 - 250216	17612	1	678975	2025-10-01 19:32:37	\N
882	2025-08-25	17914 - 240286	17914	2	679105	2025-10-01 19:32:37	\N
883	2025-08-25	17612 - 250216	17612	1	678725	2025-10-01 19:32:37	\N
884	2025-08-25	17612 - 250216	17612	2	678965	2025-10-01 19:32:37	\N
885	2025-08-25	18795 - 11001	18795	1	678715	2025-10-01 19:32:37	\N
886	2025-08-25	17612 - 250216	17612	4	678825	2025-10-01 19:32:37	\N
887	2025-08-25	17612 - 250216	17612	3	678875	2025-10-01 19:32:37	\N
888	2025-08-25	18795 - 11001	18795	1	678705	2025-10-01 19:32:37	\N
889	2025-08-25	17914 - 240286	17914	1	678795	2025-10-01 19:32:37	\N
890	2025-08-25	17612 - 250216	17612	1	678955	2025-10-01 19:32:37	\N
891	2025-08-25	17612 - 250216	17612	6	678685	2025-10-01 19:32:37	\N
892	2025-08-25	17914 - 240286	17914	1	678705	2025-10-01 19:32:37	\N
893	2025-08-25	17612 - 250216	17612	1	678945	2025-10-01 19:32:37	\N
894	2025-08-25	17612 - 250216	17612	2	679035	2025-10-01 19:32:37	\N
895	2025-08-25	17612 - 250216	17612	1	679095	2025-10-01 19:32:37	\N
896	2025-08-25	17612 - 250216	17612	1	678935	2025-10-01 19:32:37	\N
897	2025-08-25	17612 - 250216	17612	4	678865	2025-10-01 19:32:37	\N
898	2025-08-25	17612 - 250216	17612	1	678815	2025-10-01 19:32:37	\N
899	2025-08-25	17612 - 250216	17612	5	679085	2025-10-01 19:32:37	\N
900	2025-08-25	17612 - 250216	17612	10	678925	2025-10-01 19:32:37	\N
901	2025-08-25	17612 - 250216	17612	1	679025	2025-10-01 19:32:37	\N
902	2025-08-25	17612 - 250216	17612	5	678795	2025-10-01 19:32:37	\N
903	2025-08-25	17612 - 250216	17612	5	679015	2025-10-01 19:32:37	\N
904	2025-08-25	17612 - 250216	17612	6	678675	2025-10-01 19:32:37	\N
905	2025-08-25	17612 - 250216	17612	1	678855	2025-10-01 19:32:37	\N
906	2025-08-25	17612 - 250216	17612	6	678845	2025-10-01 19:32:37	\N
907	2025-08-25	17612 - 250216	17612	1	679075	2025-10-01 19:32:37	\N
908	2025-08-25	17612 - 250216	17612	1	678785	2025-10-01 19:32:37	\N
909	2025-08-25	17612 - 250216	17612	3	679065	2025-10-01 19:32:37	\N
910	2025-08-25	17612 - 250216	17612	1	678765	2025-10-01 19:32:37	\N
911	2025-08-25	17612 - 250216	17612	1	679005	2025-10-01 19:32:37	\N
912	2025-08-25	17914 - 240286	17914	1	678755	2025-10-01 19:32:37	\N
913	2025-08-25	17612 - 250216	17612	1	678995	2025-10-01 19:32:37	\N
914	2025-08-26	17612 - 250216	17612	1	679135	2025-10-01 19:32:37	\N
915	2025-08-26	17612 - 250216	17612	6	679445	2025-10-01 19:32:37	\N
916	2025-08-26	17612 - 250216	17612	1	679215	2025-10-01 19:32:37	\N
917	2025-08-26	17612 - 250216	17612	6	679205	2025-10-01 19:32:37	\N
918	2025-08-26	18795 - 11001	18795	1	679225	2025-10-01 19:32:37	\N
919	2025-08-26	17612 - 250216	17612	6	679435	2025-10-01 19:32:37	\N
920	2025-08-26	18795 - 11001	18795	1	679305	2025-10-01 19:32:37	\N
921	2025-08-26	17612 - 250216	17612	1	679295	2025-10-01 19:32:37	\N
922	2025-08-26	17612 - 250216	17612	1	679285	2025-10-01 19:32:37	\N
923	2025-08-26	17612 - 250216	17612	6	679195	2025-10-01 19:32:37	\N
924	2025-08-26	17612 - 250216	17612	3	100466	2025-10-01 19:32:37	\N
925	2025-08-26	17612 - 250216	17612	1	679355	2025-10-01 19:32:37	\N
926	2025-08-26	17612 - 250216	17612	1	679265	2025-10-01 19:32:37	\N
927	2025-08-26	17612 - 250216	17612	1	679425	2025-10-01 19:32:37	\N
929	2025-08-26	17612 - 250216	17612	1	679345	2025-10-01 19:32:37	\N
930	2025-08-26	17612 - 250216	17612	6	679255	2025-10-01 19:32:37	\N
931	2025-08-26	17612 - 250216	17612	5	679415	2025-10-01 19:32:37	\N
932	2025-08-26	17612 - 250216	17612	2	679335	2025-10-01 19:32:37	\N
933	2025-08-26	17612 - 250216	17612	2	679165	2025-10-01 19:32:37	\N
934	2025-08-26	17612 - 250216	17612	7	679185	2025-10-01 19:32:37	\N
935	2025-08-26	17612 - 250216	17612	6	679325	2025-10-01 19:32:37	\N
936	2025-08-26	17612 - 250216	17612	6	679155	2025-10-01 19:32:37	\N
937	2025-08-26	17904 - 240276	17904	1	679395	2025-10-01 19:32:37	\N
938	2025-08-26	17612 - 250216	17612	6	679385	2025-10-01 19:32:37	\N
939	2025-08-26	17612 - 250216	17612	1	679245	2025-10-01 19:32:37	\N
940	2025-08-26	17612 - 250216	17612	2	679235	2025-10-01 19:32:37	\N
941	2025-08-26	17612 - 250216	17612	6	679225	2025-10-01 19:32:37	\N
942	2025-08-26	17612 - 250216	17612	6	679315	2025-10-01 19:32:37	\N
943	2025-08-26	17612 - 250216	17612	6	679175	2025-10-01 19:32:37	\N
944	2025-08-26	17612 - 250216	17612	2	679145	2025-10-01 19:32:37	\N
945	2025-08-26	17612 - 250216	17612	2	100464	2025-10-01 19:32:37	\N
946	2025-08-26	17612 - 250216	17612	2	679375	2025-10-01 19:32:37	\N
947	2025-08-26	17612 - 250216	17612	1	679365	2025-10-01 19:32:37	\N
948	2025-08-27	17914 - 240286	17914	1	679655	2025-10-01 19:32:37	\N
949	2025-08-27	17914 - 240286	17914	1	679485	2025-10-01 19:32:37	\N
950	2025-08-27	17914 - 240286	17914	1	679735	2025-10-01 19:32:37	\N
951	2025-08-27	17612 - 250216	17612	2	679535	2025-10-01 19:32:37	\N
952	2025-08-27	17904 - 240276	17904	6	679805	2025-10-01 19:32:37	\N
953	2025-08-27	17612 - 250216	17612	6	679505	2025-10-01 19:32:37	\N
954	2025-08-27	17612 - 250216	17612	1	679815	2025-10-01 19:32:37	\N
955	2025-08-27	17612 - 250216	17612	15	679805	2025-10-01 19:32:37	\N
956	2025-08-27	17612 - 250216	17612	6	679495	2025-10-01 19:32:37	\N
957	2025-08-27	17612 - 250216	17612	6	679715	2025-10-01 19:32:37	\N
958	2025-08-27	17612 - 250216	17612	4	679485	2025-10-01 19:32:37	\N
959	2025-08-27	17612 - 250216	17612	6	679465	2025-10-01 19:32:37	\N
960	2025-08-27	18795 - 11001	18795	1	679705	2025-10-01 19:32:37	\N
961	2025-08-27	17612 - 250216	17612	1	679595	2025-10-01 19:32:37	\N
962	2025-08-27	18795 - 11001	18795	1	679655	2025-10-01 19:32:37	\N
963	2025-08-27	17612 - 250216	17612	6	679695	2025-10-01 19:32:37	\N
964	2025-08-27	17612 - 250216	17612	1	679585	2025-10-01 19:32:37	\N
965	2025-08-27	17612 - 250216	17612	1	679645	2025-10-01 19:32:37	\N
966	2025-08-27	17612 - 250216	17612	6	679575	2025-10-01 19:32:37	\N
967	2025-08-27	17612 - 250216	17612	2	679635	2025-10-01 19:32:37	\N
968	2025-08-27	17612 - 250216	17612	1	679735	2025-10-01 19:32:37	\N
969	2025-08-27	17612 - 250216	17612	6	679455	2025-10-01 19:32:37	\N
970	2025-08-27	17612 - 250216	17612	6	679625	2025-10-01 19:32:37	\N
971	2025-08-27	17612 - 250216	17612	1	679785	2025-10-01 19:32:37	\N
972	2025-08-27	18795 - 11001	18795	6	679455	2025-10-01 19:32:37	\N
973	2025-08-27	17612 - 250216	17612	1	679775	2025-10-01 19:32:37	\N
974	2025-08-27	17612 - 250216	17612	2	679685	2025-10-01 19:32:37	\N
975	2025-08-27	17612 - 250216	17612	1	679765	2025-10-01 19:32:37	\N
976	2025-08-27	17612 - 250216	17612	1	679565	2025-10-01 19:32:37	\N
977	2025-08-27	17612 - 250216	17612	1	679755	2025-10-01 19:32:37	\N
978	2025-08-27	17612 - 250216	17612	2	679555	2025-10-01 19:32:37	\N
979	2025-08-27	17612 - 250216	17612	2	679675	2025-10-01 19:32:37	\N
980	2025-08-27	17904 - 240276	17904	1	679655	2025-10-01 19:32:37	\N
981	2025-08-27	18795 - 11001	18795	1	679615	2025-10-01 19:32:37	\N
982	2025-08-27	17612 - 250216	17612	1	679745	2025-10-01 19:32:37	\N
983	2025-08-27	17612 - 250216	17612	1	679655	2025-10-01 19:32:37	\N
984	2025-08-27	17612 - 250216	17612	1	679605	2025-10-01 19:32:37	\N
985	2025-08-27	17612 - 250216	17612	1	679725	2025-10-01 19:32:37	\N
986	2025-08-27	17612 - 250216	17612	1	679545	2025-10-01 19:32:37	\N
987	2025-08-27	17612 - 250216	17612	1	679665	2025-10-01 19:32:37	\N
988	2025-08-27	17904 - 240276	17904	1	679485	2025-10-01 19:32:37	\N
989	2025-08-28	17612 - 250216	17612	2	679825	2025-10-01 19:32:37	\N
990	2025-08-28	17612 - 250216	17612	40	680055	2025-10-01 19:32:37	\N
991	2025-08-28	17612 - 250216	17612	6	679855	2025-10-01 19:32:37	\N
992	2025-08-28	17612 - 250216	17612	1	680045	2025-10-01 19:32:37	\N
993	2025-08-28	17612 - 250216	17612	6	680035	2025-10-01 19:32:37	\N
994	2025-08-28	17612 - 250216	17612	1	679895	2025-10-01 19:32:37	\N
995	2025-08-28	17612 - 250216	17612	2	679885	2025-10-01 19:32:37	\N
996	2025-08-28	17612 - 250216	17612	6	680065	2025-10-01 19:32:37	\N
997	2025-08-28	17612 - 250216	17612	1	680005	2025-10-01 19:32:37	\N
998	2025-08-28	17612 - 250216	17612	4	679845	2025-10-01 19:32:37	\N
999	2025-08-28	17612 - 250216	17612	1	679995	2025-10-01 19:32:37	\N
1000	2025-08-28	17612 - 250216	17612	1	679875	2025-10-01 19:32:37	\N
1001	2025-08-28	17612 - 250216	17612	6	679975	2025-10-01 19:32:37	\N
1002	2025-08-28	17612 - 250216	17612	6	679865	2025-10-01 19:32:37	\N
1003	2025-08-28	18795 - 11001	18795	1	679955	2025-10-01 19:32:37	\N
1004	2025-08-28	17612 - 250216	17612	6	680015	2025-10-01 19:32:37	\N
1005	2025-08-28	17612 - 250216	17612	2	679835	2025-10-01 19:32:37	\N
1006	2025-08-28	18795 - 11001	18795	1	679945	2025-10-01 19:32:37	\N
1007	2025-08-28	17914 - 240286	17914	1	679955	2025-10-01 19:32:37	\N
1008	2025-08-28	17612 - 250216	17612	2	679915	2025-10-01 19:32:37	\N
1009	2025-08-28	17904 - 240276	17904	1	679845	2025-10-01 19:32:37	\N
1010	2025-08-28	17914 - 240286	17914	1	679845	2025-10-01 19:32:37	\N
1011	2025-08-28	18795 - 11001	18795	1	679905	2025-10-01 19:32:37	\N
1012	2025-08-28	17612 - 250216	17612	1	679965	2025-10-01 19:32:37	\N
1013	2025-08-28	17914 - 240286	17914	15	679795	2025-10-01 19:32:37	\N
1014	2025-08-28	17612 - 250216	17612	6	680085	2025-10-01 19:32:37	\N
1015	2025-08-28	17914 - 240286	17914	6	679515	2025-10-01 19:32:37	\N
1016	2025-08-28	17612 - 250216	17612	1	680075	2025-10-01 19:32:37	\N
1017	2025-08-29	17612 - 250216	17612	2	680155	2025-10-01 19:32:37	\N
1018	2025-08-29	17612 - 250216	17612	15	100467	2025-10-01 19:32:37	\N
1019	2025-08-29	17612 - 250216	17612	15	680145	2025-10-01 19:32:37	\N
1020	2025-08-29	17612 - 250216	17612	2	680095	2025-10-01 19:32:37	\N
1021	2025-08-29	17612 - 250216	17612	1	680105	2025-10-01 19:32:37	\N
1022	2025-08-29	17612 - 250216	17612	1	680135	2025-10-01 19:32:37	\N
1023	2025-08-29	17612 - 250216	17612	1	680115	2025-10-01 19:32:37	\N
1024	2025-09-02	17612 - 250216	17612	1	680165	2025-10-01 19:32:37	392759698500
1025	2025-09-02	17904 - 240276	17904	1	680295	2025-10-01 19:32:37	392759745667
1026	2025-09-02	17612 - 250216	17612	20	100468	2025-10-01 19:32:37	392759718435
1027	2025-09-02	17612 - 250216	17612	1	680375	2025-10-01 19:32:37	392759733755
1028	2025-09-02	17612 - 250216	17612	2	680365	2025-10-01 19:32:37	392759728470
1029	2025-09-02	17612 - 250216	17612	6	680355	2025-10-01 19:32:37	392759720538
1030	2025-09-02	17612 - 250216	17612	1	680345	2025-10-01 19:32:37	392759717450
1031	2025-09-02	17612 - 250216	17612	15	680285	2025-10-01 19:32:37	392759698598
1032	2025-09-02	17612 - 250216	17612	15	680335	2025-10-01 19:32:37	392759696676
1033	2025-09-02	17612 - 250216	17612	1	680245	2025-10-01 19:32:37	392759709945
1034	2025-09-02	18795 - 11001	18795	3	680235	2025-10-01 19:32:37	392759706913
1035	2025-09-02	17612 - 250216	17612	3	680325	2025-10-01 19:32:37	392759704678
1036	2025-09-02	17612 - 250216	17612	6	680205	2025-10-01 19:32:37	392759697488
1037	2025-09-02	17612 - 250216	17612	1	680275	2025-10-01 19:32:37	392759705858
1038	2025-09-02	17612 - 250216	17612	6	680225	2025-10-01 19:32:37	392759697282
1039	2025-09-02	17612 - 250216	17612	3	680255	2025-10-01 19:32:37	392759700569
1040	2025-09-02	17612 - 250216	17612	3	680315	2025-10-01 19:32:37	392759699859
1041	2025-09-02	17914 - 240286	17914	1	680175	2025-10-01 19:32:37	392759698955
1042	2025-09-02	18795 - 11001	18795	2	680205	2025-10-01 19:32:37	392759697330
1043	2025-09-02	17612 - 250216	17612	1	680305	2025-10-01 19:32:37	392759695967
1044	2025-09-03	17612 - 250216	17612	6	680535	2025-10-01 19:32:37	392816988080
1045	2025-09-03	17612 - 250195	17612	2	680465	2025-10-01 19:32:37	392816992094
1046	2025-09-03	17612 - 250216	17612	1	100471	2025-10-01 19:32:37	392816991168
1047	2025-09-03	17612 - 250216	17612	1	680405	2025-10-01 19:32:37	392816991032
1048	2025-09-03	17914 - 240286	17914	1	680385	2025-10-01 19:32:37	392816990210
1049	2025-09-03	17612 - 250216	17612	1	680455	2025-10-01 19:32:37	392816988676
1050	2025-09-03	17914 - 240286	17914	1	680395	2025-10-01 19:32:37	392816988930
1051	2025-09-03	17612 - 250216	17612	2	680525	2025-10-01 19:32:37	392816986743
1052	2025-09-03	17612 - 250216	17612	3	680395	2025-10-01 19:32:37	392816984681
1053	2025-09-03	17612 - 250216	17612	6	680445	2025-10-01 19:32:37	392816982027
1054	2025-09-03	17612 - 250216	17612	6	680385	2025-10-01 19:32:37	392816981796
1055	2025-09-03	17612 - 250195	17612	2	680495	2025-10-01 19:32:37	392816983847
1056	2025-09-03	17612 - 250216	17612	3	680515	2025-10-01 19:32:37	392816983398
1057	2025-09-03	17612 - 250216	17612	1	680435	2025-10-01 19:32:37	392816984258
1058	2025-09-03	17612 - 250216	17612	1	680485	2025-10-01 19:32:37	392816983527
1059	2025-09-03	17612 - 250216	17612	1	100470	2025-10-01 19:32:37	392816981844
1060	2025-09-03	17612 - 250216	17612	1	680425	2025-10-01 19:32:37	392816983619
1061	2025-09-03	17612 - 250216	17612	1	680475	2025-10-01 19:32:37	392816982141
1062	2025-09-03	17612 - 250216	17612	1	100469	2025-10-01 19:32:37	392816980881
1063	2025-09-04	17612 - 250216	17612	2	680575	2025-10-01 19:32:37	392859993840
1064	2025-09-04	17612 - 250216	17612	16	680725	2025-10-01 19:32:37	392860026268
1065	2025-09-04	17612 - 250216	17612	6	680695	2025-10-01 19:32:37	392860017403
1066	2025-09-04	17612 - 250216	17612	1	680675	2025-10-01 19:32:37	392860018925
1067	2025-09-04	17612 - 250216	17612	6	680625	2025-10-01 19:32:37	392860014919
1068	2025-09-04	17612 - 250216	17612	1	680895	2025-10-01 19:32:37	392860018362
1069	2025-09-04	17612 - 250216	17612	1	681035	2025-10-01 19:32:37	392860017870
1070	2025-09-04	17612 - 250216	17612	6	680665	2025-10-01 19:32:37	392860012228
1071	2025-09-04	17612 - 250216	17612	6	680885	2025-10-01 19:32:37	392860009368
1072	2025-09-04	17904 - 250240	17904	3	100472	2025-10-01 19:32:37	392860014047
1073	2025-09-04	17612 - 250216	17612	1	681025	2025-10-01 19:32:37	392860014106
1074	2025-09-04	17612 - 250216	17612	6	680615	2025-10-01 19:32:37	392860007284
1075	2025-09-04	17612 - 250216	17612	1	681015	2025-10-01 19:32:37	392860013198
1076	2025-09-04	17612 - 250216	17612	1	680655	2025-10-01 19:32:37	392860010648
1077	2025-09-04	17612 - 250216	17612	2	681005	2025-10-01 19:32:37	392860009313
1078	2025-09-04	17612 - 250216	17612	1	680875	2025-10-01 19:32:37	392860011254
1079	2025-09-04	17904 - 240276	17904	2	680945	2025-10-01 19:32:37	392860009883
1080	2025-09-04	17612 - 250216	17612	15	680645	2025-10-01 19:32:37	392859992443
1081	2025-09-04	17612 - 250216	17612	6	680835	2025-10-01 19:32:37	392860004024
1082	2025-09-04	17914 - 240286	17914	1	680975	2025-10-01 19:32:37	392860007891
1083	2025-09-04	17914 - 240286	17914	1	680935	2025-10-01 19:32:37	392860007479
1084	2025-09-04	17612 - 250216	17612	1	680995	2025-10-01 19:32:37	392860006152
1085	2025-09-04	17612 - 250216	17612	3	680925	2025-10-01 19:32:37	392860002960
1086	2025-09-04	17612 - 250216	17612	1	680605	2025-10-01 19:32:37	392860004403
1087	2025-09-04	17612 - 250216	17612	6	680985	2025-10-01 19:32:37	392859998923
1088	2025-09-04	17612 - 250216	17612	2	680805	2025-10-01 19:32:37	392860004539
1089	2025-09-04	17612 - 250216	17612	2	680595	2025-10-01 19:32:37	392860001816
1090	2025-09-04	17612 - 250216	17612	1	680795	2025-10-01 19:32:37	392860002580
1091	2025-09-04	17904 - 240276	17904	1	680575	2025-10-01 19:32:37	392860002043
1092	2025-09-04	17612 - 250216	17612	6	680585	2025-10-01 19:32:37	392859996390
1093	2025-09-04	17612 - 250216	17612	2	680825	2025-10-01 19:32:37	392860001036
1094	2025-09-04	17612 - 250216	17612	3	680785	2025-10-01 19:32:37	392859999194
1095	2025-09-04	17914 - 240286	17914	4	680915	2025-10-01 19:32:37	392859996520
1096	2025-09-04	17612 - 250216	17612	6	680815	2025-10-01 19:32:37	392859993932
1097	2025-09-04	17612 - 250216	17612	1	680975	2025-10-01 19:32:37	392859997283
1098	2025-09-04	17914 - 240286	17914	1	680755	2025-10-01 19:32:37	392859997916
1099	2025-09-04	17612 - 250216	17612	2	680965	2025-10-01 19:32:37	392859995707
1100	2025-09-04	17612 - 250216	17612	1	680745	2025-10-01 19:32:37	392859995328
1101	2025-09-04	17612 - 250216	17612	3	680905	2025-10-01 19:32:37	392859994321
1102	2025-09-04	17612 - 250216	17612	2	680735	2025-10-01 19:32:37	392859992649
1103	2025-09-04	17904 - 240276	17904	2	680955	2025-10-01 19:32:37	392859992719
4422	2024-04-16		18675	1	687815	2025-10-02 20:53:05	\N
4423	2024-04-16		17612	6	687805	2025-10-02 20:53:06	\N
4424	2024-04-16		18795	1	687795	2025-10-02 20:53:06	\N
4425	2024-04-16		17612	1	687785	2025-10-02 20:53:06	\N
4426	2024-04-16		18795	1	686865	2025-10-02 20:53:07	\N
4427	2024-04-16		17612	6	686855	2025-10-02 20:53:07	\N
4428	2024-04-16		17612	15	686625	2025-10-02 20:53:07	\N
4429	2024-04-16		17612	3	686615	2025-10-02 20:53:08	\N
4430	2024-04-16		17914	1	687835	2025-10-02 21:05:10	\N
4431	2024-04-16		17612	15	687825	2025-10-02 21:05:10	\N
1125	2025-09-05	17612 - 250216	17612	3	681365	2025-10-01 19:32:37	392904032998
5014	2025-09-25	17612 - 250237	17612	1	685985	2025-10-02 22:21:26	393599201121
5059	2024-04-16		17612 - 250070	8	100505	2025-10-02 23:39:51	\N
5060	2024-04-16		17612	1	687865	2025-10-03 13:50:57	\N
5061	2024-04-16		17612	1	687855	2025-10-03 13:50:58	\N
5062	2024-04-16		17612	2	687845	2025-10-03 13:50:58	\N
5075	2024-04-16		17612 - 250237	2	100499	2025-10-03 16:34:20	\N
5080	2024-04-16		17612	2	687885	2025-10-03 17:02:36	\N
5083	2024-04-16		17612	6	687915	2025-10-03 17:19:28	\N
5084	2024-04-16		17612	4	687905	2025-10-03 17:19:29	\N
5085	2024-04-16		17612	6	687895	2025-10-03 17:19:29	\N
6013	2024-04-16		17914	1	687935	2025-10-04 04:02:20	\N
6168	2024-04-16		17612	1	687945	2025-10-06 15:44:14	\N
8209	2024-04-16		17612	1	688505	2025-10-06 17:45:11	\N
8210	2024-04-16		17904	2	688505	2025-10-06 17:45:11	\N
12261	2024-04-16		17612	6	688515	2025-10-06 18:45:12	\N
12264	2024-04-16		17612	1	688545	2025-10-06 19:45:12	\N
12266	2024-04-16		17612	1	688535	2025-10-06 19:45:12	\N
14233	2024-04-16		17612	16	688595	2025-10-06 20:45:13	\N
14234	2024-04-16		17914	2	688595	2025-10-06 20:45:13	\N
14236	2024-04-16		17612	1	688585	2025-10-06 20:45:13	\N
14238	2024-04-16		17612	1	688555	2025-10-06 20:45:13	\N
14241	2024-04-16		17612	6	688625	2025-10-06 21:45:14	\N
14243	2024-04-16		17612	15	688605	2025-10-06 21:45:14	\N
14263	2024-04-16		17612	2	688635	2025-10-06 22:45:17	\N
14324	2025-06-24	17612 - 250172	17612	6	665745	2025-10-07 05:45:41	\N
14336	2025-08-26	17612 - 250216	17612	15	100465	2025-10-09 20:49:12	\N
1105	2025-09-05	17612 - 250216	17612	1	681145	2025-10-01 19:32:37	392904058792
1106	2025-09-05	17612 - 250216	17612	6	681135	2025-10-01 19:32:37	392904052029
1107	2025-09-05	17612 - 250216	17612	1	681125	2025-10-01 19:32:37	392904051787
1108	2025-09-05	17612 - 250216	17612	5	681505	2025-10-01 19:32:37	392904046582
1109	2025-09-05	18795 - 11001	18795	2	681115	2025-10-01 19:32:37	392904048302
1110	2025-09-05	17612 - 250216	17612	1	681615	2025-10-01 19:32:37	392904047269
1111	2025-09-05	17612 - 250216	17612	6	681105	2025-10-01 19:32:37	392904043002
16204	2024-05-21	17612 - 240141	17612	1	100032	2025-10-14 17:41:55	\N
16206	2024-11-13	17612 - 240312	17612	8	100196	2025-10-15 05:23:36.295358+00	\N
16207	2024-11-13	17612 - 240312	17612	2	100197	2025-10-15 05:23:36.295358+00	\N
16208	2024-11-13	17612 - 240312	17612	8	100198	2025-10-15 05:23:36.295358+00	\N
16203	2025-07-16	17612 - 250195	17612	1	100428	2025-10-14 17:17:53	\N
1126	2025-09-05	17914 - 240286	17914	1	681105	2025-10-01 19:32:37	392904032050
1127	2025-09-05	17612 - 250216	17612	2	681275	2025-10-01 19:32:37	392904032483
1128	2025-09-05	17612 - 250216	17612	6	681065	2025-10-01 19:32:37	392904027896
5022	2025-09-25	17612 - 250237	17612	1	686095	2025-10-02 22:21:26	393599194240
5039	2025-09-26	17612 - 250237	17612	2	686265	2025-10-02 22:21:26	393639706488
15204	2025-10-08	17612 - 250300	17612	6	688945	2025-10-10 20:16:11	394046585110
17066	2025-10-13	17612 - 250300	17612	1	689625	2025-10-15 19:54:12.859575+00	394201100956
17067	2025-10-13	17612 - 250300	17612	1	689575	2025-10-15 19:54:12.859575+00	394201102341
17068	2025-10-13	17904 - 250240	17904	1	689505	2025-10-15 19:54:12.859575+00	394201102503
17069	2025-10-13	17904 - 250240	17904	1	689515	2025-10-15 19:54:12.859575+00	394201100990
17070	2025-10-13	17612 - 250300	17612	1	689595	2025-10-15 19:54:12.859575+00	394201099135
17071	2025-10-13	18795 - 11001	18795	1	689475	2025-10-15 19:54:12.859575+00	394201098757
17072	2025-10-13	17612 - 250300	17612	1	689475	2025-10-15 19:54:12.859575+00	394201098448
17073	2025-10-13	17612 - 250300	17612	1	689505	2025-10-15 19:54:12.859575+00	394201100533
17074	2025-10-14	17612 - 250300	17612	40	689895	2025-10-15 19:54:12.859575+00	394248563228
17075	2025-10-14	17904 - 250240	17904	1	689815	2025-10-15 19:54:12.859575+00	394248588107
17076	2025-10-14	17612 - 250300	17612	1	689985	2025-10-15 19:54:12.859575+00	394248586310
17077	2025-10-14	17612 - 250300	17612	2	689975	2025-10-15 19:54:12.859575+00	394248585255
17078	2025-10-14	17612 - 250300	17612	1	689965	2025-10-15 19:54:12.859575+00	394248583995
17079	2025-10-14	17612 - 250300	17612	15	689955	2025-10-15 19:54:12.859575+00	394248566536
17080	2025-10-14	17612 - 250300	17612	6	689935	2025-10-15 19:54:12.859575+00	394248577213
17081	2025-10-14	17612 - 250300	17612	1	689775	2025-10-15 19:54:12.859575+00	394248576916
1112	2025-09-05	17612 - 250216	17612	8	681605	2025-10-01 19:32:37	392904039021
1113	2025-09-05	17612 - 250216	17612	1	681495	2025-10-01 19:32:37	392904045108
1114	2025-09-05	17612 - 250216	17612	2	681485	2025-10-01 19:32:37	392904042290
1115	2025-09-05	17612 - 250216	17612	6	681385	2025-10-01 19:32:37	392904038448
1116	2025-09-05	17612 - 250216	17612	2	681095	2025-10-01 19:32:37	392904039959
1117	2025-09-05	17612 - 250216	17612	1	681475	2025-10-01 19:32:37	392904040404
1118	2025-09-05	17612 - 250216	17612	1	681465	2025-10-01 19:32:37	392904039216
1119	2025-09-05	17612 - 250216	17612	2	681085	2025-10-01 19:32:37	392904038210
1120	2025-09-05	17612 - 250216	17612	8	681455	2025-10-01 19:32:37	392904032690
1121	2025-09-05	17612 - 250216	17612	3	681595	2025-10-01 19:32:37	392904036526
1122	2025-09-05	17612 - 250216	17612	3	681375	2025-10-01 19:32:37	392904035037
1123	2025-09-05	18795 - 11001	18795	4	681075	2025-10-01 19:32:37	392904034410
1124	2025-09-05	17612 - 250216	17612	3	681585	2025-10-01 19:32:37	392904034096
1161	2025-09-05	17612 - 250216	17612	1	681185	2025-10-01 19:32:37	392904013525
1162	2025-09-05	17612 - 250216	17612	2	681295	2025-10-01 19:32:37	392904012713
1163	2025-09-05	17612 - 250216	17612	1	681625	2025-10-01 19:32:37	392904014462
1164	2025-09-05	17612 - 250216	17612	1	681175	2025-10-01 19:32:37	392904013179
1165	2025-09-05	17612 - 250216	17612	1	681395	2025-10-01 19:32:37	392904012209
1166	2025-09-05	17612 - 250216	17612	2	681285	2025-10-01 19:32:37	392904008401
1167	2025-09-05	17612 - 250216	17612	1	681165	2025-10-01 19:32:37	392904010879
1168	2025-09-05	17914 - 240286	17914	2	681155	2025-10-01 19:32:37	392905142494
1169	2025-09-05	17612 - 250216	17612	1	681155	2025-10-01 19:32:37	392905143490
1170	2025-09-08	17612 - 250216	17612	1	681735	2025-10-01 19:32:37	392977675720
1171	2025-09-08	17914 - 240286	17914	1	681975	2025-10-01 19:32:37	392977717536
1172	2025-09-08	17612 - 250216	17612	15	681995	2025-10-01 19:32:37	392977699544
1173	2025-09-08	17612 - 250216	17612	6	681925	2025-10-01 19:32:37	392977698695
1174	2025-09-08	17612 - 250216	17612	6	681915	2025-10-01 19:32:37	392977692285
1175	2025-09-08	17612 - 250216	17612	1	100474	2025-10-01 19:32:37	392977698103
1176	2025-09-08	17612 - 250216	17612	6	681885	2025-10-01 19:32:37	392977689680
1177	2025-09-08	17612 - 250216	17612	6	681985	2025-10-01 19:32:37	392977689966
1178	2025-09-08	17612 - 250216	17612	1	681845	2025-10-01 19:32:37	392977689705
1179	2025-09-08	17612 - 250216	17612	6	681905	2025-10-01 19:32:37	392977683648
17172	2025-10-15	17612 - 250300	17612	1	690305	2025-10-15 19:54:12.859575+00	394291893159
17173	2025-10-15	17612 - 250300	17612	2	690525	2025-10-15 19:54:12.859575+00	394291896695
17174	2025-10-15	17612 - 250300	17612	2	690385	2025-10-15 19:54:12.859575+00	394291894946
17175	2025-10-15	17612 - 250300	17612	4	690515	2025-10-15 19:54:12.859575+00	394291891720
17176	2025-10-15	17612 - 250300	17612	3	690375	2025-10-15 19:54:12.859575+00	394291890322
17177	2025-10-15	17612 - 250300	17612	8	690655	2025-10-15 19:54:12.859575+00	394291886959
17178	2025-10-15	17612 - 250300	17612	1	690835	2025-10-15 19:54:12.859575+00	394291892406
17179	2025-10-15	17612 - 250300	17612	1	690815	2025-10-15 19:54:12.859575+00	394291892060
17180	2025-10-15	17612 - 250300	17612	2	690505	2025-10-15 19:54:12.859575+00	394291888540
17181	2025-10-15	17612 - 250300	17612	6	690365	2025-10-15 19:54:12.859575+00	394291886043
17182	2025-10-15	17914 - 250297	17914	3	690805	2025-10-15 19:54:12.859575+00	394291886890
17183	2025-10-15	17612 - 250300	17612	6	690495	2025-10-15 19:54:12.859575+00	394291883673
17184	2025-10-15	17612 - 250300	17612	1	690795	2025-10-15 19:54:12.859575+00	394291886190
17185	2025-10-15	17612 - 250300	17612	1	690645	2025-10-15 19:54:12.859575+00	394291884680
17186	2025-10-15	17612 - 250300	17612	2	690785	2025-10-15 19:54:12.859575+00	394291884187
17187	2025-10-15	17612 - 250300	17612	1	690355	2025-10-15 19:54:12.859575+00	394291883868
17188	2025-10-15	17612 - 250300	17612	1	690635	2025-10-15 19:54:12.859575+00	394291883467
17189	2025-10-15	17612 - 250300	17612	5	690715	2025-10-15 19:54:12.859575+00	394293463412
1104	2025-09-05	17904 - 240276	17904	1	681005	2025-10-01 19:32:37	392904010559
1129	2025-09-05	17612 - 250216	17612	4	681575	2025-10-01 19:32:37	392904029498
1130	2025-09-05	18795 - 11001	18795	2	681105	2025-10-01 19:32:37	392904031580
1131	2025-09-05	17612 - 250216	17612	2	681355	2025-10-01 19:32:37	392904029535
1132	2025-09-05	17612 - 250216	17612	1	681445	2025-10-01 19:32:37	392904029156
1133	2025-09-05	17612 - 250216	17612	1	681265	2025-10-01 19:32:37	392904029145
1134	2025-09-05	17612 - 250216	17612	1	681435	2025-10-01 19:32:37	392904027922
1135	2025-09-05	17612 - 250216	17612	1	681255	2025-10-01 19:32:37	392904030388
1136	2025-09-05	17612 - 250216	17612	5	681345	2025-10-01 19:32:37	392904024463
1137	2025-09-05	17612 - 250216	17612	5	681425	2025-10-01 19:32:37	392904024279
1138	2025-09-05	17612 - 250216	17612	1	681725	2025-10-01 19:32:37	392904028745
1139	2025-09-05	17612 - 250216	17612	1	681245	2025-10-01 19:32:37	392904028333
1140	2025-09-05	17612 - 250216	17612	1	681565	2025-10-01 19:32:37	392904027635
1141	2025-09-05	17612 - 250216	17612	1	681705	2025-10-01 19:32:37	392904028160
1142	2025-09-05	17612 - 250216	17612	8	681235	2025-10-01 19:32:37	392904019350
1143	2025-09-05	17612 - 250216	17612	2	681555	2025-10-01 19:32:37	392904026260
1144	2025-09-05	17612 - 250216	17612	15	681055	2025-10-01 19:32:37	392904009691
1145	2025-09-05	17612 - 250216	17612	2	681685	2025-10-01 19:32:37	392904025779
1146	2025-09-05	17612 - 250216	17612	5	681545	2025-10-01 19:32:37	392904018870
1147	2025-09-05	17612 - 250216	17612	1	681665	2025-10-01 19:32:37	392904023787
1148	2025-09-05	17612 - 250216	17612	2	681335	2025-10-01 19:32:37	392904022942
1149	2025-09-05	17612 - 250216	17612	10	681405	2025-10-01 19:32:37	392904011625
1150	2025-09-05	17612 - 250216	17612	2	681655	2025-10-01 19:32:37	392904020744
1151	2025-09-05	17612 - 250216	17612	2	681325	2025-10-01 19:32:37	392904019177
1152	2025-09-05	17612 - 250216	17612	5	681645	2025-10-01 19:32:37	392904016682
1153	2025-09-05	17612 - 250216	17612	1	681535	2025-10-01 19:32:37	392904019946
1154	2025-09-05	17612 - 250216	17612	1	681315	2025-10-01 19:32:37	392904018928
1155	2025-09-05	17612 - 250216	17612	1	681525	2025-10-01 19:32:37	392904018012
1156	2025-09-05	17612 - 250216	17612	1	681205	2025-10-01 19:32:37	392904017049
1157	2025-09-05	17612 - 250216	17612	3	681305	2025-10-01 19:32:37	392904015881
1158	2025-09-05	17612 - 250216	17612	5	681515	2025-10-01 19:32:37	392904011897
1159	2025-09-05	17612 - 250216	17612	2	681195	2025-10-01 19:32:37	392904014337
1160	2025-09-05	17612 - 250216	17612	1	681635	2025-10-01 19:32:37	392904014153
1180	2025-09-08	17612 - 250216	17612	6	681835	2025-10-01 19:32:37	392977683409
1181	2025-09-08	17612 - 250216	17612	2	681875	2025-10-01 19:32:37	392977688320
1182	2025-09-08	17904 - 240276	17904	1	681815	2025-10-01 19:32:37	392977689083
1183	2025-09-08	17612 - 250216	17612	4	681975	2025-10-01 19:32:37	392977682940
1184	2025-09-08	17612 - 250216	17612	6	681955	2025-10-01 19:32:37	392977679726
1185	2025-09-08	17612 - 250216	17612	3	681865	2025-10-01 19:32:37	392977681884
1186	2025-09-08	17612 - 250216	17612	1	681805	2025-10-01 19:32:37	392977685890
1187	2025-09-08	17612 - 250216	17612	1	681775	2025-10-01 19:32:37	392977681830
1188	2025-09-08	17612 - 250216	17612	6	681895	2025-10-01 19:32:37	392977674621
1189	2025-09-08	17612 - 250216	17612	6	681965	2025-10-01 19:32:37	392977674838
1190	2025-09-08	17612 - 250216	17612	6	681855	2025-10-01 19:32:37	392977673717
1191	2025-09-08	17612 - 250216	17612	1	681825	2025-10-01 19:32:37	392977680660
1192	2025-09-08	17612 - 250216	17612	2	681745	2025-10-01 19:32:37	392977678086
1193	2025-09-08	17612 - 250216	17612	4	681815	2025-10-01 19:32:37	392977675812
1194	2025-09-08	17612 - 250216	17612	1	681945	2025-10-01 19:32:37	392977677962
1195	2025-09-08	17612 - 250216	17612	1	100473	2025-10-01 19:32:37	392977675639
1196	2025-09-09	17612 - 250216	17612	6	682145	2025-10-01 19:32:37	393025762100
1197	2025-09-09	17612 - 250216	17612	6	100475	2025-10-01 19:32:37	393025757019
1198	2025-09-09	17612 - 250216	17612	15	682135	2025-10-01 19:32:37	393025744199
1199	2025-09-09	17612 - 250216	17612	5	100476	2025-10-01 19:32:37	393025754546
1200	2025-09-09	17612 - 250216	17612	6	682085	2025-10-01 19:32:37	393025752690
1201	2025-09-09	17612 - 250216	17612	1	682175	2025-10-01 19:32:37	393025753506
1202	2025-09-09	17612 - 250216	17612	6	682155	2025-10-01 19:32:37	393025738160
1203	2025-09-09	17612 - 250216	17612	6	682065	2025-10-01 19:32:37	393025745541
1204	2025-09-09	17612 - 250216	17612	1	682025	2025-10-01 19:32:37	393025748047
1205	2025-09-09	17612 - 250216	17612	2	682045	2025-10-01 19:32:37	393025746099
1206	2025-09-09	17612 - 250216	17612	1	682125	2025-10-01 19:32:37	393025746868
1207	2025-09-09	17612 - 250216	17612	2	682005	2025-10-01 19:32:37	393025745449
1208	2025-09-09	17612 - 250216	17612	1	682095	2025-10-01 19:32:37	393025744854
1209	2025-09-09	17612 - 250216	17612	1	682035	2025-10-01 19:32:37	393025745048
1210	2025-09-10	17612 - 250216	17612	2	682185	2025-10-01 19:32:37	393069308394
1211	2025-09-10	17612 - 250237	17612	15	682245	2025-10-01 19:32:37	393069320627
1212	2025-09-10	17612 - 250237	17612	6	682365	2025-10-01 19:32:37	393069327470
1213	2025-09-10	17612 - 250237	17612	3	682355	2025-10-01 19:32:37	393069324574
1214	2025-09-10	17612 - 250237	17612	1	682325	2025-10-01 19:32:37	393069326062
1215	2025-09-10	17612 - 250237	17612	6	682195	2025-10-01 19:32:37	393069317610
1216	2025-09-10	17612 - 250237	17612	6	682345	2025-10-01 19:32:37	393069317344
1217	2025-09-10	17612 - 250237	17612	6	682295	2025-10-01 19:32:37	393069314665
1218	2025-09-10	17612 - 250237	17612	2	682415	2025-10-01 19:32:37	393069317631
1219	2025-09-10	17612 - 250237	17612	3	682235	2025-10-01 19:32:37	393069316532
1220	2025-09-10	17612 - 250237	17612	1	682215	2025-10-01 19:32:37	393069319440
1221	2025-09-10	17612 - 250237	17612	6	682405	2025-10-01 19:32:37	393069311427
1222	2025-09-10	17612 - 250237	17612	5	682205	2025-10-01 19:32:37	393069313280
1223	2025-09-10	17612 - 250237	17612	1	682315	2025-10-01 19:32:37	393069317149
1224	2025-09-10	17612 - 250237	17612	3	100477	2025-10-01 19:32:37	393069312088
1225	2025-09-10	17612 - 250237	17612	6	682335	2025-10-01 19:32:37	393069308681
1226	2025-09-10	17612 - 250237	17612	6	682305	2025-10-01 19:32:37	393069307869
1227	2025-09-10	17612 - 250237	17612	1	682275	2025-10-01 19:32:37	393069313084
1228	2025-09-10	17612 - 250216	17612	2	682265	2025-10-01 19:32:37	393069308843
1229	2025-09-10	18795 - 11001	18795	1	682195	2025-10-01 19:32:37	393069311840
1230	2025-09-10	17612 - 250237	17612	3	682225	2025-10-01 19:32:37	393069308111
1231	2025-09-10	17612 - 250237	17612	1	682395	2025-10-01 19:32:37	393069309460
1232	2025-09-10	17612 - 250237	17612	1	682385	2025-10-01 19:32:37	393069307571
1233	2025-09-10	18795 - 11001	18795	1	682255	2025-10-01 19:32:37	393069308383
1234	2025-09-11	17612 - 250237	17612	15	682425	2025-10-01 19:32:37	393111478313
1235	2025-09-11	17612 - 250237	17612	2	682755	2025-10-01 19:32:37	393111488645
1236	2025-09-11	17612 - 250237	17612	2	682745	2025-10-01 19:32:37	393111484444
1237	2025-09-11	17612 - 250237	17612	5	682735	2025-10-01 19:32:37	393111479099
1238	2025-09-11	17612 - 250237	17612	1	682685	2025-10-01 19:32:37	393111481478
1239	2025-09-11	17612 - 250237	17612	15	682665	2025-10-01 19:32:37	393111467338
1240	2025-09-11	17612 - 250237	17612	6	682725	2025-10-01 19:32:37	393111473080
1241	2025-09-11	17612 - 250237	17612	15	682605	2025-10-01 19:32:37	393111465438
1242	2025-09-11	17612 - 250237	17612	6	682485	2025-10-01 19:32:37	393111468459
1243	2025-09-11	17612 - 250237	17612	6	682705	2025-10-01 19:32:37	393111465129
1244	2025-09-11	17612 - 250237	17612	6	682655	2025-10-01 19:32:37	393111463376
1245	2025-09-11	17612 - 250237	17612	6	682535	2025-10-01 19:32:37	393111462119
1246	2025-09-11	17612 - 250237	17612	1	682575	2025-10-01 19:32:37	393111467371
1247	2025-09-11	17612 - 250237	17612	2	682475	2025-10-01 19:32:37	393111464795
1248	2025-09-11	17612 - 250237	17612	1	682565	2025-10-01 19:32:37	393111464203
1249	2025-09-11	17612 - 250237	17612	6	682555	2025-10-01 19:32:37	393111459914
1250	2025-09-11	17612 - 250237	17612	6	682455	2025-10-01 19:32:37	393111459719
1251	2025-09-11	17612 - 250237	17612	3	682595	2025-10-01 19:32:37	393111462380
1252	2025-09-11	17612 - 250237	17612	6	682695	2025-10-01 19:32:37	393111457738
1253	2025-09-11	17612 - 250237	17612	5	682645	2025-10-01 19:32:37	393111458208
1254	2025-09-11	17612 - 250237	17612	1	682515	2025-10-01 19:32:37	393111461693
14325	2025-09-11	17612 - 250237	17612	2	682585	2025-10-07 05:45:41	393111458572
1256	2025-09-11	17612 - 250237	17612	2	682505	2025-10-01 19:32:37	393111458756
1257	2025-09-11	17612 - 250237	17612	2	682545	2025-10-01 19:32:37	393111457727
1258	2025-09-11	17612 - 250237	17612	1	682495	2025-10-01 19:32:37	393111458090
1259	2025-09-11	17612 - 250237	17612	1	682445	2025-10-01 19:32:37	393111458778
1260	2025-09-11	18795 - 11001	18795	1	100478	2025-10-01 19:32:37	393111851774
1261	2025-09-12	17612 - 250237	17612	1	680635	2025-10-01 19:32:37	393150581640
1262	2025-09-12	17612 - 250237	17612	6	682765	2025-10-01 19:32:37	393150621486
1263	2025-09-12	17612 - 250237	17612	14	100480	2025-10-01 19:32:37	393150614061
1264	2025-09-12	17914 - 250297	17914	15	682665	2025-10-01 19:32:37	393150610250
1265	2025-09-12	17914 - 250297	17914	2	100481	2025-10-01 19:32:37	393150611945
1266	2025-09-12	17612 - 250237	17612	12	100481	2025-10-01 19:32:37	393150601966
1267	2025-09-12	17914 - 250297	17914	2	682465	2025-10-01 19:32:37	393150605608
1268	2025-09-12	18795 - 11001	18795	1	682905	2025-10-01 19:32:37	393150607883
1269	2025-09-12	17914 - 250297	17914	10	682425	2025-10-01 19:32:37	393150598863
1270	2025-09-12	17612 - 250237	17612	1	682895	2025-10-01 19:32:37	393150603009
1271	2025-09-12	17612 - 250237	17612	15	682885	2025-10-01 19:32:37	393150593302
1272	2025-09-12	17914 - 250297	17914	2	100480	2025-10-01 19:32:37	393150600168
1273	2025-09-12	17612 - 250237	17612	14	100479	2025-10-01 19:32:37	393150588119
1274	2025-09-12	17612 - 250237	17612	6	682835	2025-10-01 19:32:37	393150594401
1275	2025-09-12	17914 - 250297	17914	2	100483	2025-10-01 19:32:37	393150597514
1276	2025-09-12	17914 - 250297	17914	1	682375	2025-10-01 19:32:37	393150597363
1277	2025-09-12	17914 - 250297	17914	2	682285	2025-10-01 19:32:37	393150596106
1278	2025-09-12	17612 - 250237	17612	1	682985	2025-10-01 19:32:37	393150596415
1279	2025-09-12	17914 - 250297	17914	1	100475	2025-10-01 19:32:37	393150594960
1280	2025-09-12	17612 - 250237	17612	4	682965	2025-10-01 19:32:37	393150592784
1281	2025-09-12	17914 - 250297	17914	15	682165	2025-10-01 19:32:37	393150581651
1282	2025-09-12	17914 - 250297	17914	1	682055	2025-10-01 19:32:37	393150594364
1283	2025-09-12	17914 - 250297	17914	2	100479	2025-10-01 19:32:37	393150591906
1284	2025-09-12	17914 - 250297	17914	2	681905	2025-10-01 19:32:37	393150592188
1285	2025-09-12	17612 - 250237	17612	2	682875	2025-10-01 19:32:37	393150590380
1286	2025-09-12	17612 - 250237	17612	1	682955	2025-10-01 19:32:37	393150590965
1287	2025-09-12	17612 - 250237	17612	2	682815	2025-10-01 19:32:37	393150589869
1288	2025-09-12	17914 - 250297	17914	1	681815	2025-10-01 19:32:37	393150571135
1289	2025-09-12	17612 - 250237	17612	6	682945	2025-10-01 19:32:37	393150585999
1290	2025-09-12	18795 - 11001	18795	2	682865	2025-10-01 19:32:37	393150588233
1291	2025-09-12	17914 - 250297	17914	3	681795	2025-10-01 19:32:37	393150587958
1292	2025-09-12	17612 - 250237	17612	1	682805	2025-10-01 19:32:37	393150588440
1293	2025-09-12	17612 - 250237	17612	2	682795	2025-10-01 19:32:37	393150586230
1294	2025-09-12	17612 - 250237	17612	2	682855	2025-10-01 19:32:37	393150586594
1295	2025-09-12	17914 - 250297	17914	1	682965	2025-10-01 19:32:37	393150572381
1296	2025-09-12	17914 - 250297	17914	6	681755	2025-10-01 19:32:37	393150582463
1297	2025-09-12	17612 - 250216	17612	2	682905	2025-10-01 19:32:37	393150585267
1298	2025-09-12	17612 - 250237	17612	6	682775	2025-10-01 19:32:37	393150581397
1299	2025-09-12	17612 - 250237	17612	6	682845	2025-10-01 19:32:37	393150581386
1300	2025-09-12	17612 - 250237	17612	4	682925	2025-10-01 19:32:37	393150583036
1301	2025-09-12	17612 - 250237	17612	4	100484	2025-10-01 19:32:37	393150581993
1302	2025-09-12	17612 - 250237	17612	1	682915	2025-10-01 19:32:37	393150581375
1303	2025-09-15	17904 - 250240	17904	1	681975	2025-10-01 19:32:37	393220230663
1304	2025-09-15	17612 - 250237	17612	5	683695	2025-10-01 19:32:37	393220299298
1305	2025-09-15	17612 - 250237	17612	1	683845	2025-10-01 19:32:37	393220300192
1306	2025-09-15	17612 - 250237	17612	1	683835	2025-10-01 19:32:37	393220298133
1307	2025-09-15	17612 - 250237	17612	5	683685	2025-10-01 19:32:37	393220291687
1308	2025-09-15	17612 - 250237	17612	6	683805	2025-10-01 19:32:37	393220289643
1309	2025-09-15	17612 - 250237	17612	1	683675	2025-10-01 19:32:37	393220289816
1310	2025-09-15	17904 - 250240	17904	1	683175	2025-10-01 19:32:37	393220286140
1311	2025-09-15	18675 - 240231	18675	1	683665	2025-10-01 19:32:37	393220288669
1312	2025-09-15	17914 - 250297	17914	1	683705	2025-10-01 19:32:37	393220286920
1313	2025-09-15	17612 - 250237	17612	10	683655	2025-10-01 19:32:37	393220274570
1314	2025-09-15	17914 - 250297	17914	1	683115	2025-10-01 19:32:37	393220285019
14326	2025-09-15	17612 - 250237	17612	2	683035	2025-10-07 05:45:41	393220282318
1316	2025-09-15	17914 - 250297	17914	2	683015	2025-10-01 19:32:37	393220281815
1317	2025-09-15	17612 - 250237	17612	1	683025	2025-10-01 19:32:37	393220280245
1318	2025-09-15	17612 - 250237	17612	5	683825	2025-10-01 19:32:37	393220273666
1319	2025-09-15	17612 - 250237	17612	10	683015	2025-10-01 19:32:37	393220267281
1320	2025-09-15	17612 - 250237	17612	1	683545	2025-10-01 19:32:37	393220277320
1321	2025-09-15	17612 - 250237	17612	1	683535	2025-10-01 19:32:37	393220277525
1322	2025-09-15	17612 - 250237	17612	1	683215	2025-10-01 19:32:37	393220273026
1323	2025-09-15	17612 - 250237	17612	1	683525	2025-10-01 19:32:37	393220276301
1324	2025-09-15	17914 - 250297	17914	3	683205	2025-10-01 19:32:37	393220270851
1325	2025-09-15	17612 - 250237	17612	1	683515	2025-10-01 19:32:37	393220274824
1326	2025-09-15	17612 - 250237	17612	6	683815	2025-10-01 19:32:37	393220266220
1327	2025-09-15	17612 - 250237	17612	3	683645	2025-10-01 19:32:37	393220269788
1328	2025-09-15	17612 - 250237	17612	6	683485	2025-10-01 19:32:37	393220266149
1329	2025-09-15	17914 - 250297	17914	1	683195	2025-10-01 19:32:37	393220270380
1330	2025-09-15	17612 - 250237	17612	1	683175	2025-10-01 19:32:37	393220270005
1331	2025-09-15	17612 - 250237	17612	2	683635	2025-10-01 19:32:37	393220267719
1332	2025-09-15	17612 - 250237	17612	1	683375	2025-10-01 19:32:37	393220269619
1333	2025-09-15	17904 - 250240	17904	1	683165	2025-10-01 19:32:37	393220268873
1334	2025-09-15	17612 - 250237	17612	2	683365	2025-10-01 19:32:37	393220266686
1335	2025-09-15	17612 - 250237	17612	6	683155	2025-10-01 19:32:37	393220259684
1336	2025-09-15	17914 - 250297	17914	2	683005	2025-10-01 19:32:37	393220263610
1337	2025-09-15	17612 - 250237	17612	2	683625	2025-10-01 19:32:37	393220264823
1338	2025-09-15	17904 - 250240	17904	1	683805	2025-10-01 19:32:37	393220265532
1339	2025-09-15	17612 - 250237	17612	1	683475	2025-10-01 19:32:37	393220264639
1340	2025-09-15	17612 - 250237	17612	2	683355	2025-10-01 19:32:37	393220263676
1341	2025-09-15	17904 - 250240	17904	1	683795	2025-10-01 19:32:37	393220264591
1342	2025-09-15	18795 - 11001	18795	1	682995	2025-10-01 19:32:37	393220263069
1343	2025-09-15	17612 - 250237	17612	3	683615	2025-10-01 19:32:37	393220259868
1344	2025-09-15	17612 - 250237	17612	2	683465	2025-10-01 19:32:37	393220260622
1345	2025-09-15	17612 - 250237	17612	5	683775	2025-10-01 19:32:37	393220257730
1346	2025-09-15	17904 - 250240	17904	5	100480	2025-10-01 19:32:37	393220254811
1347	2025-09-15	17612 - 250237	17612	2	683345	2025-10-01 19:32:37	393220260004
1348	2025-09-15	17612 - 250237	17612	1	683455	2025-10-01 19:32:37	393220260644
1349	2025-09-15	17612 - 250237	17612	1	683135	2025-10-01 19:32:37	393220259170
1350	2025-09-15	17612 - 250237	17612	3	683605	2025-10-01 19:32:37	393220254134
1351	2025-09-15	17612 - 250237	17612	1	683335	2025-10-01 19:32:37	393220258541
1352	2025-09-15	17612 - 250237	17612	5	683445	2025-10-01 19:32:37	393220253642
1353	2025-09-15	17612 - 250237	17612	6	683125	2025-10-01 19:32:37	393220250584
1354	2025-09-15	17612 - 250237	17612	2	683325	2025-10-01 19:32:37	393220255656
1355	2025-09-15	17612 - 250237	17612	7	683765	2025-10-01 19:32:37	393220249319
1356	2025-09-15	17904 - 250240	17904	5	100479	2025-10-01 19:32:37	393220247062
1357	2025-09-15	17612 - 250237	17612	3	683595	2025-10-01 19:32:37	393220251694
1358	2025-09-15	17612 - 250237	17612	3	683315	2025-10-01 19:32:37	393220251021
1359	2025-09-15	17612 - 250237	17612	3	683435	2025-10-01 19:32:37	393220245130
1360	2025-09-15	17612 - 250237	17612	7	683585	2025-10-01 19:32:37	393220243479
1361	2025-09-15	17612 - 250237	17612	1	683115	2025-10-01 19:32:37	393220249570
1362	2025-09-15	17612 - 250237	17612	1	683305	2025-10-01 19:32:37	393220248540
1363	2025-09-15	17904 - 250240	17904	1	682965	2025-10-01 19:32:37	393220248312
1364	2025-09-15	17612 - 250237	17612	6	683105	2025-10-01 19:32:37	393220241682
1365	2025-09-15	17612 - 250237	17612	4	683425	2025-10-01 19:32:37	393220243516
1366	2025-09-15	17612 - 250237	17612	1	683295	2025-10-01 19:32:37	393220243814
1367	2025-09-15	17612 - 250237	17612	1	683755	2025-10-01 19:32:37	393220246640
1368	2025-09-15	17904 - 250240	17904	1	682925	2025-10-01 19:32:37	393220246629
1369	2025-09-15	17612 - 250237	17612	2	683275	2025-10-01 19:32:37	393220242483
1370	2025-09-15	17612 - 250237	17612	1	683745	2025-10-01 19:32:37	393220245791
1371	2025-09-15	17612 - 250237	17612	3	100482	2025-10-01 19:32:37	393220243365
1372	2025-09-15	17612 - 250237	17612	5	683735	2025-10-01 19:32:37	393220238701
1373	2025-09-15	17612 - 250237	17612	1	683265	2025-10-01 19:32:37	393220243457
1374	2025-09-15	17612 - 250237	17612	6	683415	2025-10-01 19:32:37	393220235790
1375	2025-09-15	17612 - 250237	17612	2	683575	2025-10-01 19:32:37	393220240826
1376	2025-09-15	17612 - 250237	17612	1	683255	2025-10-01 19:32:37	393220241936
1377	2025-09-15	17904 - 250240	17904	5	100481	2025-10-01 19:32:37	393220236293
1378	2025-09-15	18795 - 11001	18795	2	683085	2025-10-01 19:32:37	393220240609
1379	2025-09-15	17612 - 250237	17612	3	683245	2025-10-01 19:32:37	393220237679
1380	2025-09-15	17612 - 250237	17612	3	683565	2025-10-01 19:32:37	393220236661
1381	2025-09-15	17914 - 250297	17914	1	683075	2025-10-01 19:32:37	393220238870
1382	2025-09-15	17612 - 250237	17612	1	683725	2025-10-01 19:32:37	393220237933
1383	2025-09-15	17612 - 250237	17612	2	683065	2025-10-01 19:32:37	393220235253
1384	2025-09-15	17612 - 250237	17612	1	683715	2025-10-01 19:32:37	393220236639
1385	2025-09-15	17612 - 250237	17612	1	683235	2025-10-01 19:32:37	393220235297
1386	2025-09-15	17904 - 250240	17904	1	682675	2025-10-01 19:32:37	393220235106
1387	2025-09-15	17612 - 250237	17612	1	683405	2025-10-01 19:32:37	393220235091
1388	2025-09-15	17612 - 250237	17612	4	683555	2025-10-01 19:32:37	393220232427
1389	2025-09-15	17612 - 250237	17612	4	683705	2025-10-01 19:32:37	393220231225
1390	2025-09-15	17612 - 250237	17612	4	683225	2025-10-01 19:32:37	393220232221
1391	2025-09-15	17904 - 250240	17904	1	682545	2025-10-01 19:32:37	393220234095
1392	2025-09-15	17612 - 250237	17612	2	683055	2025-10-01 19:32:37	393220232677
1393	2025-09-15	17612 - 250237	17612	2	683395	2025-10-01 19:32:37	393220232471
1394	2025-09-15	17904 - 250240	17904	1	682385	2025-10-01 19:32:37	393220233732
1395	2025-09-15	17612 - 250237	17612	1	683045	2025-10-01 19:32:37	393220231924
1396	2025-09-15	17612 - 250237	17612	1	683385	2025-10-01 19:32:37	393220231214
1397	2025-09-16	17612 - 250237	17612	6	683855	2025-10-01 19:32:37	393265962181
1398	2025-09-16	17914 - 250297	17914	1	684075	2025-10-01 19:32:37	393265995757
1399	2025-09-16	18795 - 11001	18795	1	100485	2025-10-01 19:32:37	393265996525
1400	2025-09-16	17612 - 250237	17612	15	684065	2025-10-01 19:32:37	393265981235
1401	2025-09-16	18795 - 11001	18795	3	683935	2025-10-01 19:32:37	393265994419
1402	2025-09-16	17914 - 250297	17914	1	683895	2025-10-01 19:32:37	393265993592
1403	2025-09-16	17612 - 250237	17612	1	684155	2025-10-01 19:32:37	393265989810
1404	2025-09-16	17612 - 250237	17612	6	684145	2025-10-01 19:32:37	393265985150
1405	2025-09-16	17612 - 250237	17612	6	100486	2025-10-01 19:32:37	393265982210
1406	2025-09-16	17612 - 250237	17612	2	683955	2025-10-01 19:32:37	393265984120
1407	2025-09-16	17612 - 250237	17612	6	684135	2025-10-01 19:32:37	393265979360
1408	2025-09-16	17612 - 250237	17612	6	683935	2025-10-01 19:32:37	393265977313
1409	2025-09-16	17612 - 250237	17612	4	684115	2025-10-01 19:32:37	393265977861
1410	2025-09-16	17914 - 250297	17914	1	684055	2025-10-01 19:32:37	393265979533
1411	2025-09-16	17612 - 250237	17612	6	684015	2025-10-01 19:32:37	393265976340
1412	2025-09-16	17612 - 250237	17612	15	684045	2025-10-01 19:32:37	393265963545
1413	2025-09-16	17612 - 250237	17612	6	683895	2025-10-01 19:32:37	393265974038
1414	2025-09-16	17612 - 250237	17612	15	684125	2025-10-01 19:32:37	393265961120
1415	2025-09-16	17612 - 250237	17612	6	100485	2025-10-01 19:32:37	393265969175
1416	2025-09-16	17612 - 250237	17612	6	683925	2025-10-01 19:32:37	393265970076
1417	2025-09-16	17612 - 250237	17612	1	684005	2025-10-01 19:32:37	393265973292
1418	2025-09-16	17612 - 250237	17612	6	683995	2025-10-01 19:32:37	393265967312
1419	2025-09-16	17914 - 250297	17914	1	683885	2025-10-01 19:32:37	393265972447
1420	2025-09-16	17612 - 250237	17612	1	683875	2025-10-01 19:32:37	393265971039
1421	2025-09-16	17612 - 250237	17612	6	683915	2025-10-01 19:32:37	393265960260
1422	2025-09-16	17914 - 250297	17914	1	683865	2025-10-01 19:32:37	393265969337
1423	2025-09-16	17612 - 250237	17612	1	684095	2025-10-01 19:32:37	393265967985
1424	2025-09-16	17612 - 250237	17612	6	684085	2025-10-01 19:32:37	393265960866
1425	2025-09-16	17612 - 250237	17612	2	683985	2025-10-01 19:32:37	393265964184
1426	2025-09-16	17612 - 250237	17612	1	684035	2025-10-01 19:32:37	393265962012
1427	2025-09-16	17612 - 250237	17612	1	683905	2025-10-01 19:32:37	393265962674
1428	2025-09-16	17612 - 250237	17612	1	683965	2025-10-01 19:32:37	393265962766
1429	2025-09-17	17612 - 250237	17612	6	684165	2025-10-01 19:32:37	393313010005
1430	2025-09-17	17612 - 250237	17612	40	684425	2025-10-01 19:32:37	393313045098
1431	2025-09-17	17612 - 250237	17612	8	100489	2025-10-01 19:32:37	393313040854
1432	2025-09-17	17612 - 250237	17612	25	684415	2025-10-01 19:32:37	393313022384
1433	2025-09-17	18795 - 11001	18795	3	684255	2025-10-01 19:32:37	393313038935
1434	2025-09-17	17612 - 250237	17612	8	100488	2025-10-01 19:32:37	393313031687
1435	2025-09-17	18795 - 11001	18795	4	684375	2025-10-01 19:32:37	393313035811
1436	2025-09-17	17914 - 250297	17914	1	684195	2025-10-01 19:32:37	393313034355
1437	2025-09-17	17914 - 250297	17914	1	684395	2025-10-01 19:32:37	393313032065
1438	2025-09-17	17904 - 250240	17904	1	684355	2025-10-01 19:32:37	393313030842
1439	2025-09-17	17612 - 250237	17612	6	684455	2025-10-01 19:32:37	393313026460
1440	2025-09-17	17612 - 250237	17612	12	100491	2025-10-01 19:32:37	393313020727
1441	2025-09-17	17612 - 250237	17612	6	684205	2025-10-01 19:32:37	393313025740
1442	2025-09-17	17612 - 250237	17612	15	100487	2025-10-01 19:32:37	393313012339
1443	2025-09-17	17612 - 250237	17612	6	684365	2025-10-01 19:32:37	393313019790
1444	2025-09-17	17612 - 250237	17612	6	684195	2025-10-01 19:32:37	393313019892
1445	2025-09-17	17612 - 250237	17612	6	684405	2025-10-01 19:32:37	393313018072
1446	2025-09-17	17612 - 250237	17612	1	684285	2025-10-01 19:32:37	393313020430
1447	2025-09-17	17612 - 250237	17612	8	100490	2025-10-01 19:32:37	393313014250
1448	2025-09-17	17612 - 250237	17612	1	684265	2025-10-01 19:32:37	393313018245
1449	2025-09-17	17612 - 250237	17612	1	684355	2025-10-01 19:32:37	393313019079
1450	2025-09-17	17612 - 250237	17612	1	684185	2025-10-01 19:32:37	393313018657
1451	2025-09-17	17612 - 250237	17612	6	684255	2025-10-01 19:32:37	393313013703
1452	2025-09-17	17612 - 250237	17612	2	684345	2025-10-01 19:32:37	393313016698
1453	2025-09-17	18795 - 11001	18795	2	684175	2025-10-01 19:32:37	393313017580
1454	2025-09-17	17612 - 250237	17612	6	684335	2025-10-01 19:32:37	393313011207
1455	2025-09-17	17612 - 250237	17612	1	684385	2025-10-01 19:32:37	393313016974
1456	2025-09-17	17612 - 250237	17612	5	684375	2025-10-01 19:32:37	393313009994
1457	2025-09-17	17612 - 250237	17612	4	684465	2025-10-01 19:32:37	393313011229
1458	2025-09-17	17612 - 250237	17612	2	684235	2025-10-01 19:32:37	393313011402
1459	2025-09-17	17612 - 250237	17612	2	684445	2025-10-01 19:32:37	393313009961
1460	2025-09-17	17612 - 250237	17612	1	684215	2025-10-01 19:32:37	393313009435
1461	2025-09-17	17612 - 250237	17612	1	684325	2025-10-01 19:32:37	393313010510
4976	2025-09-18	17612 - 250237	17612	1	684475	2025-10-02 22:21:25	393352325687
1463	2025-09-18	17612 - 250237	17612	15	684505	2025-10-01 19:32:37	393352327110
1464	2025-09-18	17612 - 250237	17612	6	684585	2025-10-01 19:32:37	393352337912
1465	2025-09-18	17612 - 250237	17612	6	684605	2025-10-01 19:32:37	393352333777
1466	2025-09-18	17612 - 250237	17612	6	684555	2025-10-01 19:32:37	393352331914
1467	2025-09-18	17612 - 250237	17612	3	684575	2025-10-01 19:32:37	393352331682
1468	2025-09-18	17612 - 250237	17612	5	684535	2025-10-01 19:32:37	393352328653
1469	2025-09-18	17612 - 250237	17612	6	684635	2025-10-01 19:32:37	393352326937
1470	2025-09-18	17612 - 250237	17612	6	684565	2025-10-01 19:32:37	393352324327
1471	2025-09-18	17612 - 250237	17612	2	684615	2025-10-01 19:32:37	393352329421
1472	2025-09-18	17612 - 250237	17612	1	684545	2025-10-01 19:32:37	393352330024
1473	2025-09-18	17612 - 250237	17612	4	100492	2025-10-01 19:32:37	393352325573
1474	2025-09-18	17904 - 250240	17904	1	684605	2025-10-01 19:32:37	393352328767
1475	2025-09-18	17612 - 250237	17612	1	684525	2025-10-01 19:32:37	393352327326
1476	2025-09-18	17612 - 250237	17612	1	684495	2025-10-01 19:32:37	393352326396
1477	2025-09-18	17612 - 250237	17612	2	684595	2025-10-01 19:32:37	393352325470
1478	2025-09-18	17612 - 250237	17612	1	684625	2025-10-01 19:32:37	393352321155
1479	2025-09-18	17914 - 250297	17914	1	684515	2025-10-01 19:32:37	393352324614
4623	2025-09-19	17612 - 250237	17612	1	684645	2025-10-02 21:41:15	393395076009
4637	2025-09-19	17612 - 250237	17612	1	684785	2025-10-02 21:41:16	393395092520
4636	2025-09-19	17612 - 250237	17612	6	684775	2025-10-02 21:41:16	393395088080
4635	2025-09-19	17612 - 250237	17612	6	684765	2025-10-02 21:41:16	393395082622
5701	2025-09-19	17612 - 250237	17612	6	684695	2025-10-03 18:05:18	393395077428
4634	2025-09-19	17612 - 250237	17612	6	684755	2025-10-02 21:41:16	393395078078
4632	2025-09-19	17612 - 250237	17612	6	684725	2025-10-02 21:41:16	393395076914
5704	2025-09-19	17904 - 250240	17904	1	684695	2025-10-03 18:05:18	393395081843
4633	2025-09-19	17612 - 250237	17612	6	684735	2025-10-02 21:41:16	393395075929
4626	2025-09-19	17612 - 250237	17612	2	684675	2025-10-02 21:41:15	393395078012
4625	2025-09-19	17612 - 250237	17612	2	684665	2025-10-02 21:41:15	393395074999
4630	2025-09-19	17914 - 250297	17914	2	684695	2025-10-02 21:41:15	393395075631
4627	2025-09-19	17612 - 250237	17612	2	684685	2025-10-02 21:41:15	393395075734
4624	2025-09-19	17612 - 250237	17612	1	684655	2025-10-02 21:41:15	393395075697
4631	2025-09-19	17914 - 250297	17914	1	684715	2025-10-02 21:41:16	393395074874
4638	2025-09-22	17612 - 250237	17612	2	684795	2025-10-02 21:41:16	393466732792
5713	2025-09-22	17612 - 250237	17612	2	684945	2025-10-03 18:05:18	393466776508
4651	2025-09-22	17612 - 250237	17612	15	684935	2025-10-02 21:41:16	393466757112
5715	2025-09-22	17612 - 250237	17612	15	684925	2025-10-03 18:05:18	393466732998
4640	2025-09-22	17612 - 250237	17612	5	684815	2025-10-02 21:41:16	393466746159
4667	2025-09-22	17612 - 250237	17612	6	100493	2025-10-02 21:41:17	393466745884
4643	2025-09-22	17612 - 250237	17612	1	684855	2025-10-02 21:41:16	393466747730
4642	2025-09-22	17612 - 250237	17612	2	684835	2025-10-02 21:41:16	393466743480
4639	2025-09-22	17612 - 250237	17612	6	684805	2025-10-02 21:41:16	393466737408
4645	2025-09-22	17612 - 250237	17612	6	684875	2025-10-02 21:41:16	393466737268
4641	2025-09-22	17914 - 250297	17914	6	684825	2025-10-02 21:41:16	393466734497
4654	2025-09-22	17612 - 250237	17612	1	684955	2025-10-02 21:41:16	393466739628
4648	2025-09-22	17612 - 250237	17612	1	684915	2025-10-02 21:41:16	393466741043
4653	2025-09-22	17914 - 250297	17914	1	684945	2025-10-02 21:41:16	393466738573
4647	2025-09-22	17612 - 250237	17612	2	684905	2025-10-02 21:41:16	393466736217
4650	2025-09-22	17914 - 250297	17914	2	684925	2025-10-02 21:41:16	393466735770
4646	2025-09-22	17612 - 250237	17612	1	684885	2025-10-02 21:41:16	393466734865
4644	2025-09-22	17612 - 250237	17612	1	684865	2025-10-02 21:41:16	393466734420
4686	2025-09-23	17612 - 250237	17612	15	685275	2025-10-02 21:41:17	393514518332
4680	2025-09-23	17612 - 250237	17612	4	685205	2025-10-02 21:41:17	393514517715
4685	2025-09-23	17914 - 250297	17914	1	685265	2025-10-02 21:41:17	393514517027
4674	2025-09-23	17612 - 250237	17612	15	685135	2025-10-02 21:41:17	393514500812
4679	2025-09-23	17612 - 250237	17612	6	685195	2025-10-02 21:41:17	393514512209
4661	2025-09-23	17612 - 250237	17612	2	685015	2025-10-02 21:41:17	393514515127
4684	2025-09-23	17612 - 250237	17612	2	685255	2025-10-02 21:41:17	393514515116
4660	2025-09-23	17612 - 250237	17612	6	685005	2025-10-02 21:41:17	393514508684
4683	2025-09-23	17612 - 250237	17612	1	685225	2025-10-02 21:41:17	393514514359
4706	2025-09-23	17612 - 250237	17612	8	100495	2025-10-02 21:41:18	393514505505
4678	2025-09-23	17612 - 250237	17612	3	685185	2025-10-02 21:41:17	393514508971
4659	2025-09-23	17612 - 250237	17612	1	684995	2025-10-02 21:41:17	393514504575
4677	2025-09-23	17612 - 250237	17612	15	685165	2025-10-02 21:41:17	393514493482
14328	2025-09-23	18795 - 11001	18795	1	684985	2025-10-07 05:45:41	393514506924
14853	2025-09-23	17612 - 250237	17612	1	684985	2025-10-10 20:16:11	393514502745
4665	2025-09-23	17612 - 250237	17612	2	685045	2025-10-02 21:41:17	393514504634
4656	2025-09-23	17914 - 250297	17914	1	684975	2025-10-02 21:41:16	393514505034
5747	2025-09-23	17612 - 250237	17612	15	685215	2025-10-03 18:05:18	393514490369
4655	2025-09-23	17612 - 250237	17612	15	684965	2025-10-02 21:41:16	393514491722
4669	2025-09-23	17612 - 250237	17612	6	685075	2025-10-02 21:41:17	393514498278
4689	2025-09-23	17914 - 250297	17914	2	685295	2025-10-02 21:41:18	393514501278
4692	2025-09-23	17612 - 250237	17612	6	100494	2025-10-02 21:41:18	393514497146
4682	2025-09-23	17904 - 250240	17904	3	685215	2025-10-02 21:41:17	393514498484
4690	2025-09-23	17612 - 250237	17612	1	685305	2025-10-02 21:41:18	393514498315
4668	2025-09-23	17612 - 250237	17612	1	685065	2025-10-02 21:41:17	393514496389
5755	2025-09-23	17612 - 250237	17612	6	685295	2025-10-03 18:05:18	393514491045
4666	2025-09-23	17612 - 250237	17612	1	685055	2025-10-02 21:41:17	393514497000
4673	2025-09-23	17612 - 250237	17612	1	685125	2025-10-02 21:41:17	393514495290
4672	2025-09-23	17612 - 250237	17612	1	685105	2025-10-02 21:41:17	393514493817
5759	2025-09-23	17914 - 250297	17914	2	685045	2025-10-03 18:05:18	393514494250
4671	2025-09-23	17612 - 250237	17612	2	685095	2025-10-02 21:41:17	393514492340
4676	2025-09-23	17612 - 250237	17612	1	685155	2025-10-02 21:41:17	393514491078
4663	2025-09-23	17612 - 250237	17612	2	685035	2025-10-02 21:41:17	393514489582
4675	2025-09-23	17612 - 250237	17612	2	685145	2025-10-02 21:41:17	393514491332
4670	2025-09-23	17612 - 250237	17612	2	685085	2025-10-02 21:41:17	393514488760
4687	2025-09-23	17612 - 250237	17612	1	685285	2025-10-02 21:41:17	393514491620
4662	2025-09-23	17612 - 250237	17612	1	685025	2025-10-02 21:41:17	393514490895
4701	2025-09-24	17612 - 250237	17612	6	685405	2025-10-02 21:41:18	393557021500
4712	2025-09-24	17612 - 250237	17612	17	100498	2025-10-02 21:41:18	393556999631
4700	2025-09-24	17612 - 250237	17612	1	685395	2025-10-02 21:41:18	393557020397
4699	2025-09-24	17612 - 250237	17612	6	685385	2025-10-02 21:41:18	393557014807
4709	2025-09-24	17612 - 250237	17612	6	685495	2025-10-02 21:41:18	393557014303
4698	2025-09-24	17612 - 250237	17612	15	685375	2025-10-02 21:41:18	393556996643
4708	2025-09-24	17612 - 250237	17612	1	685485	2025-10-02 21:41:18	393557012469
4693	2025-09-24	17612 - 250237	17612	1	685325	2025-10-02 21:41:18	393557011500
4707	2025-09-24	17612 - 250237	17612	6	685475	2025-10-02 21:41:18	393557005640
4696	2025-09-24	17612 - 250237	17612	6	685355	2025-10-02 21:41:18	393557005570
4695	2025-09-24	17612 - 250237	17612	6	685345	2025-10-02 21:41:18	393556998234
4705	2025-09-24	17612 - 250237	17612	6	685465	2025-10-02 21:41:18	393556995029
4710	2025-09-24	17904 - 250240	17904	1	100497	2025-10-02 21:41:18	393557002104
4703	2025-09-24	17612 - 250237	17612	1	685445	2025-10-02 21:41:18	393557001152
4711	2025-09-24	17914 - 250297	17914	3	100496	2025-10-02 21:41:18	393556996194
4694	2025-09-24	17612 - 250237	17612	1	685335	2025-10-02 21:41:18	393556996312
4704	2025-09-24	17612 - 250237	17612	2	685455	2025-10-02 21:41:18	393556994927
5784	2025-09-24	17904 - 250240	17904	1	685505	2025-10-03 18:05:18	393556994504
4691	2025-09-24	18795 - 11001	18795	1	685315	2025-10-02 21:41:18	393556995095
4697	2025-09-24	17904 - 250240	17904	1	685365	2025-10-02 21:41:18	393556995100
4702	2025-09-24	17904 - 250240	17904	1	685415	2025-10-02 21:41:18	393556995945
4718	2025-09-24	17904 - 250240	17904	2	685555	2025-10-02 21:41:19	393557014119
4714	2025-09-24	17612 - 250237	17612	1	685505	2025-10-02 21:41:18	393557012127
4717	2025-09-24	17612 - 250237	17612	6	685545	2025-10-02 21:41:18	393557005618
4721	2025-09-24	17904 - 250240	17904	2	685575	2025-10-02 21:41:19	393557008617
4724	2025-09-24	18795 - 11001	18795	1	685605	2025-10-02 21:41:19	393557007518
4723	2025-09-24	17612 - 250237	17612	1	685595	2025-10-02 21:41:19	393557002582
4722	2025-09-24	17612 - 250237	17612	1	685585	2025-10-02 21:41:19	393557005743
4716	2025-09-24	17612 - 250237	17612	1	685525	2025-10-02 21:41:18	393557003199
5796	2025-09-24	17612 - 250237	17612	2	685575	2025-10-03 18:05:18	393556999918
4715	2025-09-24	17612 - 250237	17612	6	685515	2025-10-02 21:41:18	393556996676
4719	2025-09-24	17612 - 250237	17612	6	685565	2025-10-02 21:41:19	393556995084
5799	2025-09-25	17612 - 250237	17612	6	685615	2025-10-03 18:05:18	393599191046
4989	2025-09-25	17612 - 250237	17612	6	685715	2025-10-02 22:21:25	393599245304
4988	2025-09-25	17612 - 250237	17612	1	685705	2025-10-02 22:21:25	393599244341
4987	2025-09-25	17612 - 250237	17612	3	685685	2025-10-02 22:21:25	393599241000
5803	2025-09-25	17612 - 250237	17612	15	685675	2025-10-03 18:05:18	393599227280
5020	2025-09-25	17612 - 250237	17612	1	686055	2025-10-02 22:21:26	393599235760
5019	2025-09-25	17612 - 250237	17612	3	686035	2025-10-02 22:21:26	393599233767
5018	2025-09-25	17612 - 250237	17612	6	686025	2025-10-02 22:21:26	393599227496
5029	2025-09-25	17612 - 250237	17612	3	686165	2025-10-02 22:21:26	393599230150
5028	2025-09-25	17612 - 250237	17612	6	686155	2025-10-02 22:21:26	393599224340
5017	2025-09-25	17612 - 250237	17612	20	686015	2025-10-02 22:21:26	393599208240
4984	2025-09-25	17612 - 250237	17612	6	685665	2025-10-02 22:21:25	393599220311
4986	2025-09-25	17904 - 250240	17904	1	685675	2025-10-02 22:21:25	393599223972
4982	2025-09-25	17904 - 250240	17904	1	685645	2025-10-02 22:21:25	393599223939
5010	2025-09-25	17612 - 250237	17612	6	685945	2025-10-02 22:21:26	393599218458
5027	2025-09-25	17612 - 250237	17612	6	686145	2025-10-02 22:21:26	393599218653
4978	2025-09-25	17914 - 250297	17914	1	685615	2025-10-02 22:21:25	393599223159
4991	2025-09-25	17914 - 250297	17914	1	685745	2025-10-02 22:21:25	393599220778
5000	2025-09-25	17612 - 250237	17612	1	685845	2025-10-02 22:21:25	393599219811
4983	2025-09-25	17612 - 250237	17612	6	685655	2025-10-02 22:21:25	393599215996
4999	2025-09-25	17612 - 250237	17612	5	685835	2025-10-02 22:21:25	393599215963
5035	2025-09-25	18795 - 11001	18795	1	686235	2025-10-02 22:21:26	393599218035
5034	2025-09-25	17612 - 250237	17612	6	686225	2025-10-02 22:21:26	393599213478
5009	2025-09-25	17612 - 250237	17612	3	685935	2025-10-02 22:21:26	393599215069
5026	2025-09-25	17612 - 250237	17612	6	686135	2025-10-02 22:21:26	393599210023
5824	2025-09-25	17612 - 250237	17612	15	685645	2025-10-03 18:05:18	393599202507
4998	2025-09-25	17612 - 250237	17612	2	685815	2025-10-02 22:21:25	393599212324
5008	2025-09-25	17612 - 250237	17612	5	685925	2025-10-02 22:21:26	393599210663
4997	2025-09-25	17612 - 250237	17612	3	685805	2025-10-02 22:21:25	393599210766
5033	2025-09-25	17612 - 250237	17612	6	686215	2025-10-02 22:21:26	393599206991
4996	2025-09-25	17612 - 250237	17612	2	685795	2025-10-02 22:21:25	393599207380
5025	2025-09-25	17612 - 250237	17612	6	686125	2025-10-02 22:21:26	393599204598
5007	2025-09-25	17612 - 250237	17612	2	685915	2025-10-02 22:21:25	393599208560
5016	2025-09-25	17612 - 250237	17612	6	686005	2025-10-02 22:21:26	393599203845
4995	2025-09-25	17612 - 250237	17612	1	685785	2025-10-02 22:21:25	393599206682
5006	2025-09-25	17914 - 250297	17914	1	685905	2025-10-02 22:21:25	393599207586
4994	2025-09-25	17612 - 250237	17612	4	685775	2025-10-02 22:21:25	393599200993
5032	2025-09-25	17612 - 250237	17612	6	686195	2025-10-02 22:21:26	393599201187
5005	2025-09-25	17612 - 250237	17612	1	685895	2025-10-02 22:21:25	393599205929
5004	2025-09-25	17612 - 250237	17612	1	685885	2025-10-02 22:21:25	393599205080
5024	2025-09-25	17612 - 250237	17612	6	686115	2025-10-02 22:21:26	393599199334
5003	2025-09-25	17612 - 250237	17612	1	685875	2025-10-02 22:21:25	393599203580
5002	2025-09-25	17612 - 250237	17612	1	685865	2025-10-02 22:21:25	393599202194
5015	2025-09-25	17612 - 250237	17612	1	685995	2025-10-02 22:21:26	393599202172
4993	2025-09-25	17612 - 250237	17612	2	685765	2025-10-02 22:21:25	393599200629
5001	2025-09-25	17612 - 250237	17612	10	685855	2025-10-02 22:21:25	393599192513
4980	2025-09-25	17904 - 250240	17904	1	685635	2025-10-02 22:21:25	393599200700
5049	2025-09-25	17612 - 250237	17612	1	100500	2025-10-02 22:21:27	393599200560
4979	2025-09-25	17914 - 250297	17914	2	685625	2025-10-02 22:21:25	393599199323
4992	2025-09-25	17612 - 250237	17612	3	685755	2025-10-02 22:21:25	393599197217
5013	2025-09-25	17612 - 250237	17612	5	685975	2025-10-02 22:21:26	393599195144
5031	2025-09-25	17612 - 250237	17612	6	686185	2025-10-02 22:21:26	393599193266
5023	2025-09-25	17612 - 250237	17612	3	686105	2025-10-02 22:21:26	393599195350
5853	2025-09-25	17612 - 250237	17612	5	685745	2025-10-03 18:05:18	393599193082
5012	2025-09-25	17612 - 250237	17612	1	685965	2025-10-02 22:21:26	393599193370
5021	2025-09-25	17612 - 250237	17612	2	686085	2025-10-02 22:21:26	393599193185
5011	2025-09-25	17612 - 250237	17612	2	685955	2025-10-02 22:21:26	393599191252
5030	2025-09-25	17612 - 250237	17612	1	686175	2025-10-02 22:21:26	393599192719
5047	2025-09-25	17612 - 250237	17612	2	100499	2025-10-02 22:21:27	393600297581
5037	2025-09-25	17904 - 250240	17904	1	686245	2025-10-02 22:21:26	393604131216
5861	2025-09-25	17914 - 250297	17914	1	686245	2025-10-03 18:05:18	393604131477
1645	2025-09-26	17612 - 250237	17612	1	686505	2025-10-01 19:32:37	393639716938
5054	2025-09-26	17914 - 250297	17914	1	100501	2025-10-02 22:21:27	393639718632
1647	2025-09-26	17612 - 250237	17612	1	686495	2025-10-01 19:32:37	393639716320
5052	2025-09-26	18795 - 11001	18795	1	686485	2025-10-02 22:21:27	393639716743
5051	2025-09-26	17612 - 250237	17612	6	686465	2025-10-02 22:21:27	393639711465
5867	2025-09-26	17612 - 250237	17612	6	100501	2025-10-03 18:05:18	393639710377
5046	2025-09-26	17612 - 250237	17612	6	686425	2025-10-02 22:21:27	393639707500
5050	2025-09-26	18795 - 11001	18795	3	686455	2025-10-02 22:21:27	393639708506
5040	2025-09-26	17612 - 250237	17612	5	686275	2025-10-02 22:21:27	393639703217
5044	2025-09-26	17612 - 250237	17612	2	686385	2025-10-02 22:21:27	393639704143
5043	2025-09-26	17904 - 250240	17904	2	686365	2025-10-02 22:21:27	393639706010
5042	2025-09-26	18795 - 11001	18795	1	686325	2025-10-02 22:21:27	393639707418
5048	2025-09-26	17914 - 250297	17914	2	686445	2025-10-02 22:21:27	393639706499
5045	2025-09-26	17612 - 250237	17612	1	686415	2025-10-02 22:21:27	393639704989
5041	2025-09-26	17612 - 250237	17612	1	686315	2025-10-02 22:21:27	393639704967
1662	2025-09-29	17612 - 250237	17612	6	686645	2025-10-01 19:32:37	393709631177
5055	2025-09-29	17612 - 250237	17612	6	100502	2025-10-02 22:21:27	393709623890
1664	2025-09-29	17612 - 250237	17612	15	686635	2025-10-01 19:32:37	393709607242
1665	2025-09-29	17612 - 250237	17612	1	686575	2025-10-01 19:32:37	393709618478
1666	2025-09-29	18795 - 11001	18795	3	686535	2025-10-01 19:32:37	393709615160
1667	2025-09-29	17612 - 250237	17612	6	686555	2025-10-01 19:32:37	393709610617
1668	2025-09-29	17612 - 250237	17612	1	686605	2025-10-01 19:32:37	393709616762
1669	2025-09-29	18795 - 11001	18795	1	686595	2025-10-01 19:32:37	393709614163
1670	2025-09-29	17612 - 250237	17612	6	686525	2025-10-01 19:32:37	393709607919
1671	2025-09-29	17612 - 250237	17612	6	686585	2025-10-01 19:32:37	393709607139
1672	2025-09-29	17612 - 250237	17612	3	686545	2025-10-01 19:32:37	393709606680
1673	2025-09-29	17612 - 250237	17612	1	686665	2025-10-01 19:32:37	393709608385
1674	2025-09-29	17914 - 250297	17914	1	686515	2025-10-01 19:32:37	393709606761
1675	2025-09-29	17612 - 250237	17612	1	686655	2025-10-01 19:32:37	393709605504
1676	2025-09-29	17904 - 250240	17904	1	686705	2025-10-01 19:32:37	393709628983
5056	2025-09-29	17612 - 250237	17612	1	100503	2025-10-02 22:21:27	393709627792
1678	2025-09-29	17612 - 250237	17612	15	686695	2025-10-01 19:32:37	393709608396
1679	2025-09-29	17914 - 250297	17914	1	686675	2025-10-01 19:32:37	393709610720
1680	2025-09-29	17612 - 250237	17612	1	686685	2025-10-01 19:32:37	393709606831
1681	2025-09-30	17612 - 250237	17612	1	686715	2025-10-01 19:32:37	393758674362
1682	2025-09-30	17612 - 250237	17612	1	686905	2025-10-01 19:32:37	393758695614
1683	2025-09-30	17612 - 250237	17612	6	686895	2025-10-01 19:32:37	393758688645
1684	2025-09-30	18795 - 11001	18795	1	686875	2025-10-01 19:32:37	393758687064
1685	2025-09-30	17612 - 250237	17612	6	686845	2025-10-01 19:32:37	393758680232
1686	2025-09-30	17612 - 250237	17612	6	686755	2025-10-01 19:32:37	393758681776
1687	2025-09-30	17612 - 250237	17612	6	686775	2025-10-01 19:32:37	393758677155
1688	2025-09-30	17914 - 250297	17914	6	686735	2025-10-01 19:32:37	393758675303
1689	2025-09-30	17612 - 250237	17612	6	686795	2025-10-01 19:32:37	393758661991
1690	2025-09-30	17612 - 250237	17612	6	686745	2025-10-01 19:32:37	393758674638
1691	2025-09-30	17612 - 250237	17612	6	686825	2025-10-01 19:32:37	393758673907
1692	2025-09-30	17612 - 250237	17612	2	686765	2025-10-01 19:32:37	393758674189
1693	2025-09-30	17612 - 250237	17612	1	686815	2025-10-01 19:32:37	393758675082
1694	2025-09-30	17612 - 250237	17612	1	686785	2025-10-01 19:32:37	393758673973
1695	2025-09-30	17914 - 250297	17914	1	686805	2025-10-01 19:32:37	393758673918
1696	2025-10-01	18795 - 11001	18795	1	686725	2025-10-01 19:32:37	393802743550
1697	2025-10-01	17612 - 250237	17612	6	687185	2025-10-01 19:32:37	393802780095
1698	2025-10-01	17612 - 250237	17612	6	687175	2025-10-01 19:32:37	393802776298
1699	2025-10-01	17612 - 250237	17612	1	687155	2025-10-01 19:32:37	393802773910
1700	2025-10-01	17612 - 250237	17612	6	687145	2025-10-01 19:32:37	393802768212
1701	2025-10-01	17612 - 250237	17612	1	687075	2025-10-01 19:32:37	393802770793
1702	2025-10-01	17612 - 250237	17612	1	687055	2025-10-01 19:32:37	393802767444
14331	2025-10-01	17612 - 250237	17612	6	687045	2025-10-07 05:45:41	393802762660
1704	2025-10-01	17612 - 250237	17612	16	687125	2025-10-01 19:32:37	393802751559
1705	2025-10-01	17612 - 250237	17612	6	687035	2025-10-01 19:32:37	393802758027
1706	2025-10-01	17612 - 250237	17612	1	687025	2025-10-01 19:32:37	393802755131
1707	2025-10-01	17612 - 250237	17612	1	686985	2025-10-01 19:32:37	393802755598
1708	2025-10-01	17612 - 250237	17612	1	687015	2025-10-01 19:32:37	393802754238
1709	2025-10-01	17612 - 250237	17612	1	686965	2025-10-01 19:32:37	393802751560
1710	2025-10-01	17612 - 250237	17612	5	687005	2025-10-01 19:32:37	393802748357
1711	2025-10-01	17612 - 250237	17612	4	686975	2025-10-01 19:32:37	393802749044
1712	2025-10-01	17612 - 250237	17612	2	687105	2025-10-01 19:32:37	393802751401
1713	2025-10-01	17612 - 250237	17612	6	687095	2025-10-01 19:32:37	393802743594
1714	2025-10-01	17612 - 250237	17612	1	686955	2025-10-01 19:32:37	393802747280
1715	2025-10-01	17612 - 250237	17612	6	686995	2025-10-01 19:32:37	393802743080
1716	2025-10-01	17612 - 250237	17612	1	686945	2025-10-01 19:32:37	393802745932
1717	2025-10-01	17612 - 250237	17612	1	686925	2025-10-01 19:32:37	393802745049
1718	2025-10-01	17612 - 250237	17612	1	686915	2025-10-01 19:32:37	393802741915
1719	2025-10-01	17612 - 250237	17612	1	687085	2025-10-01 19:32:37	393802743675
1720	2025-10-01	17612 - 250237	17612	1	687305	2025-10-01 19:32:37	393802772958
1721	2025-10-01	17612 - 250237	17612	1	687385	2025-10-01 19:32:37	393802772811
1722	2025-10-01	17612 - 250237	17612	3	687295	2025-10-01 19:32:37	393802770576
1723	2025-10-01	17612 - 250237	17612	4	687375	2025-10-01 19:32:37	393802767606
1724	2025-10-01	17612 - 250237	17612	2	687285	2025-10-01 19:32:37	393802765430
1725	2025-10-01	17612 - 250237	17612	3	687365	2025-10-01 19:32:37	393802763416
1726	2025-10-01	17612 - 250237	17612	1	687275	2025-10-01 19:32:37	393802766562
1727	2025-10-01	17612 - 250237	17612	1	687265	2025-10-01 19:32:37	393802765213
1728	2025-10-01	17612 - 250237	17612	15	687245	2025-10-01 19:32:37	393802751386
1729	2025-10-01	17612 - 250237	17612	2	687355	2025-10-01 19:32:37	393802763747
1730	2025-10-01	17612 - 250237	17612	1	687345	2025-10-01 19:32:37	393802761332
1731	2025-10-01	17914 - 250297	17914	1	686945	2025-10-01 19:32:37	393802760873
1732	2025-10-01	17612 - 250237	17612	1	687335	2025-10-01 19:32:37	393802759490
1733	2025-10-01	17914 - 250297	17914	3	686995	2025-10-01 19:32:37	393802758830
1734	2025-10-01	17612 - 250237	17612	1	687325	2025-10-01 19:32:37	393802759652
1735	2025-10-01	17612 - 250237	17612	16	687315	2025-10-01 19:32:37	393802743171
1736	2025-10-01	17914 - 250297	17914	2	687125	2025-10-01 19:32:37	393802756090
1737	2025-10-01	17612 - 250237	17612	2	687415	2025-10-01 19:32:37	393802752062
1738	2025-10-01	17612 - 250237	17612	1	687405	2025-10-01 19:32:37	393802750346
1739	2025-10-01	17612 - 250237	17612	6	687395	2025-10-01 19:32:37	393802746192
1740	2025-10-01	17612 - 250237	17612	6	687205	2025-10-01 19:32:37	393802745678
1741	2025-10-01	17914 - 250297	17914	1	687375	2025-10-01 19:32:37	393802744763
14332	2025-10-01	17612 - 250237	17612	1	687195	2025-10-07 05:45:41	393802744330
1743	2025-10-01	17904 - 250240	17904	1	687375	2025-10-01 19:32:37	393802744053
3495	2025-10-02	17612 - 250237	17612	6	687585	2025-10-02 17:18:52	393841922544
3496	2025-10-02	17612 - 250237	17612	15	687705	2025-10-02 17:18:52	393841914215
3497	2025-10-02	17612 - 250237	17612	6	687555	2025-10-02 17:18:52	393841916354
3498	2025-10-02	17904 - 250240	17904	1	687775	2025-10-02 17:18:52	393841921022
3499	2025-10-02	17914 - 250297	17914	1	687775	2025-10-02 17:18:52	393841919732
3500	2025-10-02	17612 - 250237	17612	4	687775	2025-10-02 17:18:52	393841917096
3501	2025-10-02	17612 - 250237	17612	6	687665	2025-10-02 17:18:52	393841912602
3502	2025-10-02	17612 - 250237	17612	6	687545	2025-10-02 17:18:52	393841909422
3503	2025-10-02	17612 - 250237	17612	6	687465	2025-10-02 17:18:52	393841910573
3504	2025-10-02	17612 - 250237	17612	6	687735	2025-10-02 17:18:52	393841909400
3505	2025-10-02	17612 - 250237	17612	1	687695	2025-10-02 17:18:52	393841913480
3506	2025-10-02	17612 - 250237	17612	2	687685	2025-10-02 17:18:52	393841909227
3507	2025-10-02	17612 - 250237	17612	1	687645	2025-10-02 17:18:52	393841910404
3508	2025-10-02	17612 - 250237	17612	3	687625	2025-10-02 17:18:52	393841910161
3509	2025-10-02	17612 - 250237	17612	1	687605	2025-10-02 17:18:52	393841910345
3510	2025-10-02	17612 - 250237	17612	6	687675	2025-10-02 17:18:52	393841905287
3511	2025-10-02	17612 - 250237	17612	6	687615	2025-10-02 17:18:52	393841904188
3512	2025-10-02	17612 - 250237	17612	6	687485	2025-10-02 17:18:52	393841905276
3513	2025-10-02	17612 - 250237	17612	4	687725	2025-10-02 17:18:52	393841906489
3514	2025-10-02	17612 - 250237	17612	3	687455	2025-10-02 17:18:52	393841907198
3515	2025-10-02	18795 - 11001	18795	1	687635	2025-10-02 17:18:52	393841907820
5057	2025-10-02	17612 - 250237	17612	1	100504	2025-10-02 22:21:27	393841908139
3517	2025-10-02	17612 - 250237	17612	1	687435	2025-10-02 17:18:52	393841905840
3518	2025-10-02	17612 - 250237	17612	2	687595	2025-10-02 17:18:52	393841904898
3519	2025-10-02	17612 - 250237	17612	1	687425	2025-10-02 17:18:52	393841904810
3520	2025-10-02	17612 - 250237	17612	1	687715	2025-10-02 17:18:52	393841905184
14333	2025-10-02	17612 - 250237	17612	2	686255	2025-10-07 05:45:41	393845889124
14329	2025-10-03	17612 - 250237	17612	2	686065	2025-10-07 05:45:41	393880548963
15098	2025-10-03	17914 - 250297	17914	1	687835	2025-10-10 20:16:11	393880562740
15099	2025-10-03	17612 - 250237	17612	15	687825	2025-10-10 20:16:11	393880549157
15100	2025-10-03	18675 - 240231	18675	1	687815	2025-10-10 20:16:11	393880556446
5992	2025-10-03	17612 - 250237	17612	8	100505	2025-10-03 18:05:18	393880548860
15102	2025-10-03	17612 - 250237	17612	6	687805	2025-10-10 20:16:11	393880549190
15103	2025-10-03	17612 - 250237	17612	1	687785	2025-10-10 20:16:11	393880551179
15104	2025-10-03	17612 - 250237	17612	2	687885	2025-10-10 20:16:11	393880548849
15105	2025-10-03	17612 - 250237	17612	1	687855	2025-10-10 20:16:11	393880549352
15106	2025-10-03	17612 - 250237	17612	2	687845	2025-10-10 20:16:11	393880547599
15107	2025-10-03	18795 - 11001	18795	1	687795	2025-10-10 20:16:11	393880547897
15108	2025-10-03	17612 - 250237	17612	1	687865	2025-10-10 20:16:11	393880548790
15109	2025-10-07	17914 - 250297	17914	1	687935	2025-10-10 20:16:11	393978472486
15110	2025-10-07	17612 - 250300	17612	1	688645	2025-10-10 20:16:11	393978488408
15111	2025-10-07	17612 - 250300	17612	4	688475	2025-10-10 20:16:11	393978486633
15112	2025-10-07	17612 - 250300	17612	40	688525	2025-10-10 20:16:11	393978478933
15113	2025-10-07	17612 - 250300	17612	15	688495	2025-10-10 20:16:11	393978480153
15114	2025-10-07	17612 - 250300	17612	6	688485	2025-10-10 20:16:11	393978478407
15115	2025-10-07	17612 - 250300	17612	3	688465	2025-10-10 20:16:11	393978477617
15116	2025-10-07	17612 - 250300	17612	1	688185	2025-10-10 20:16:11	393978480392
15117	2025-10-07	17612 - 250300	17612	10	688175	2025-10-10 20:16:11	393978476985
15118	2025-10-07	17612 - 250300	17612	6	688455	2025-10-10 20:16:11	393978478083
15119	2025-10-07	17904 - 250240	17904	2	688505	2025-10-10 20:16:11	393978478657
14334	2025-10-07	17612 - 250300	17612	6	100506	2025-10-07 08:43:12	393978477396
15121	2025-10-07	17612 - 250300	17612	2	688295	2025-10-10 20:16:11	393978477569
15122	2025-10-07	17612 - 250300	17612	2	688285	2025-10-10 20:16:11	393978477400
15123	2025-10-07	17612 - 250300	17612	2	688445	2025-10-10 20:16:11	393978478234
15124	2025-10-07	17612 - 250300	17612	2	688635	2025-10-10 20:16:11	393978475176
15125	2025-10-07	17612 - 250300	17612	5	688275	2025-10-10 20:16:11	393978475739
15126	2025-10-07	17612 - 250300	17612	5	688435	2025-10-10 20:16:11	393978469917
15127	2025-10-07	17612 - 250300	17612	1	688385	2025-10-10 20:16:11	393978477065
15128	2025-10-07	17612 - 250300	17612	6	688625	2025-10-10 20:16:11	393978476930
15129	2025-10-07	17612 - 250300	17612	1	688165	2025-10-10 20:16:11	393978476780
15130	2025-10-07	17612 - 250300	17612	1	688375	2025-10-10 20:16:11	393978477466
15131	2025-10-07	17612 - 250300	17612	6	688155	2025-10-10 20:16:11	393978476893
15132	2025-10-07	17612 - 250300	17612	1	688035	2025-10-10 20:16:11	393978477536
15133	2025-10-07	17612 - 250300	17612	7	688365	2025-10-10 20:16:11	393978475463
15134	2025-10-07	18795 - 11001	18795	2	688025	2025-10-10 20:16:11	393978470597
15135	2025-10-07	17612 - 250300	17612	5	688265	2025-10-10 20:16:11	393978476492
15136	2025-10-07	17612 - 250300	17612	2	688015	2025-10-10 20:16:11	393978476996
15137	2025-10-07	17612 - 250300	17612	5	688425	2025-10-10 20:16:11	393978476106
15138	2025-10-07	17612 - 250300	17612	15	688605	2025-10-10 20:16:11	393978473482
15139	2025-10-07	17914 - 250297	17914	1	688005	2025-10-10 20:16:11	393978476713
15140	2025-10-07	17612 - 250300	17612	2	688145	2025-10-10 20:16:11	393978467741
15141	2025-10-07	17612 - 250300	17612	7	687995	2025-10-10 20:16:11	393978474114
15142	2025-10-07	17612 - 250300	17612	2	688355	2025-10-10 20:16:11	393978475544
15143	2025-10-07	17612 - 250300	17612	1	688105	2025-10-10 20:16:11	393978475923
15144	2025-10-07	17612 - 250300	17612	1	688255	2025-10-10 20:16:11	393978475257
15145	2025-10-07	17612 - 250300	17612	5	688095	2025-10-10 20:16:11	393978474228
15146	2025-10-07	18795 - 11001	18795	1	688245	2025-10-10 20:16:11	393978474537
15147	2025-10-07	17612 - 250300	17612	2	688345	2025-10-10 20:16:11	393978473622
15148	2025-10-07	17612 - 250300	17612	3	688415	2025-10-10 20:16:11	393978475213
15149	2025-10-07	17612 - 250300	17612	1	688235	2025-10-10 20:16:11	393978473633
15150	2025-10-07	17612 - 250300	17612	1	688225	2025-10-10 20:16:11	393978475691
15151	2025-10-07	17612 - 250300	17612	4	688335	2025-10-10 20:16:11	393978474673
15152	2025-10-07	17612 - 250300	17612	5	688405	2025-10-10 20:16:11	393978473520
15153	2025-10-07	17612 - 250300	17612	7	688215	2025-10-10 20:16:11	393978473666
15154	2025-10-07	17612 - 250300	17612	2	687985	2025-10-10 20:16:11	393978474088
15155	2025-10-07	18795 - 11001	18795	2	688085	2025-10-10 20:16:11	393978474456
15156	2025-10-07	17612 - 250300	17612	2	688325	2025-10-10 20:16:11	393978473758
15157	2025-10-07	17612 - 250300	17612	3	687975	2025-10-10 20:16:11	393978472946
15158	2025-10-07	17612 - 250300	17612	1	688075	2025-10-10 20:16:11	393978473519
15159	2025-10-07	17612 - 250300	17612	1	688395	2025-10-10 20:16:11	393978474055
15160	2025-10-07	17612 - 250300	17612	5	688065	2025-10-10 20:16:11	393978472898
15161	2025-10-07	17612 - 250300	17612	3	688315	2025-10-10 20:16:11	393978473287
15162	2025-10-07	18795 - 11001	18795	6	688475	2025-10-10 20:16:11	393978471870
15163	2025-10-07	17612 - 250300	17612	2	688595	2025-10-10 20:16:11	393978472762
15164	2025-10-07	17612 - 250300	17612	2	687965	2025-10-10 20:16:11	393978473541
15165	2025-10-07	17612 - 250300	17612	1	688205	2025-10-10 20:16:11	393978471983
15166	2025-10-07	17914 - 250297	17914	5	688195	2025-10-10 20:16:11	393978470531
15167	2025-10-07	17612 - 250300	17612	5	688305	2025-10-10 20:16:11	393978471170
15168	2025-10-07	17612 - 250300	17612	1	688585	2025-10-10 20:16:11	393978471376
15169	2025-10-07	17612 - 250300	17612	2	687955	2025-10-10 20:16:11	393978470987
15170	2025-10-07	17612 - 250300	17612	1	688555	2025-10-10 20:16:11	393978472410
15171	2025-10-07	17612 - 250300	17612	3	688055	2025-10-10 20:16:11	393978472111
15172	2025-10-07	17612 - 250300	17612	1	688545	2025-10-10 20:16:11	393978472707
15173	2025-10-07	17612 - 250300	17612	1	687945	2025-10-10 20:16:11	393978471273
15174	2025-10-07	18795 - 11001	18795	1	688645	2025-10-10 20:16:11	393978472291
15175	2025-10-07	17612 - 250300	17612	1	688535	2025-10-10 20:16:11	393978471262
15176	2025-10-07	17612 - 250237	17612	6	688655	2025-10-10 20:16:11	394000025289
15177	2025-10-07	17612 - 250237	17612	1	688705	2025-10-10 20:16:11	394000042638
15178	2025-10-07	17612 - 250237	17612	15	688735	2025-10-10 20:16:11	394000025830
15179	2025-10-07	17612 - 250237	17612	1	688665	2025-10-10 20:16:11	394000033747
15180	2025-10-07	17612 - 250237	17612	6	688695	2025-10-10 20:16:11	394000027888
15181	2025-10-07	17904 - 250240	17904	2	688725	2025-10-10 20:16:11	394000027899
15182	2025-10-07	17612 - 250237	17612	1	688715	2025-10-10 20:16:11	394000027660
15183	2025-10-07	17914 - 250297	17914	1	688695	2025-10-10 20:16:11	394000027855
15184	2025-10-07	17914 - 250297	17914	1	688735	2025-10-10 20:16:11	394000025175
15185	2025-10-07	17612 - 250237	17612	1	688685	2025-10-10 20:16:11	394000025841
14335	2025-10-07	17904 - 250240	17904	1	100507	2025-10-07 21:32:36	394000025370
15187	2025-10-07	17914 - 250297	17914	1	688705	2025-10-10 20:16:11	394000023893
15188	2025-10-08	17612 - 250300	17612	40	688795	2025-10-10 20:16:11	394046592145
15189	2025-10-08	17904 - 250240	17904	6	688785	2025-10-10 20:16:11	394046584456
15190	2025-10-08	17612 - 250300	17612	1	688765	2025-10-10 20:16:11	394046583942
15191	2025-10-08	17914 - 250297	17914	6	688755	2025-10-10 20:16:11	394046576790
15192	2025-10-08	18795 - 11001	18795	1	688745	2025-10-10 20:16:11	394046576220
14337	2025-10-08	17612 - 250237	17612	3	100508	2025-10-09 20:49:12	394046604852
15194	2025-10-08	17904 - 250240	17904	2	688795	2025-10-10 20:16:11	394046603010
15195	2025-10-08	17612 - 250300	17612	1	689025	2025-10-10 20:16:11	394046603731
15196	2025-10-08	17612 - 250300	17612	15	689015	2025-10-10 20:16:11	394046585257
15197	2025-10-08	17914 - 250297	17914	6	688795	2025-10-10 20:16:11	394046595133
15198	2025-10-08	17612 - 250300	17612	6	688965	2025-10-10 20:16:11	394046593943
15199	2025-10-08	18795 - 11001	18795	1	688835	2025-10-10 20:16:11	394046594402
15200	2025-10-08	17612 - 250300	17612	1	688845	2025-10-10 20:16:11	394046590852
15201	2025-10-08	17612 - 250300	17612	6	689065	2025-10-10 20:16:11	394046585853
15202	2025-10-08	17612 - 250300	17612	1	688955	2025-10-10 20:16:11	394046592340
15203	2025-10-08	17612 - 250300	17612	6	688835	2025-10-10 20:16:11	394046585121
15205	2025-10-08	17612 - 250300	17612	1	688895	2025-10-10 20:16:11	394046586301
15206	2025-10-08	17612 - 250300	17612	1	688885	2025-10-10 20:16:11	394046585235
15207	2025-10-08	17612 - 250300	17612	1	689055	2025-10-10 20:16:11	394046583346
15208	2025-10-08	17612 - 250300	17612	2	688925	2025-10-10 20:16:11	394046582730
15209	2025-10-08	17914 - 250297	17914	1	688825	2025-10-10 20:16:11	394046583633
15210	2025-10-08	17612 - 250300	17612	5	688875	2025-10-10 20:16:11	394046578303
15211	2025-10-08	17914 - 250297	17914	1	688995	2025-10-10 20:16:11	394046584114
15212	2025-10-08	17612 - 250300	17612	1	689045	2025-10-10 20:16:11	394046582291
15213	2025-10-08	17612 - 250300	17612	1	688815	2025-10-10 20:16:11	394046582270
15214	2025-10-08	17612 - 250300	17612	1	688985	2025-10-10 20:16:11	394046581571
15215	2025-10-08	17612 - 250300	17612	6	689035	2025-10-10 20:16:11	394046576425
15216	2025-10-08	17612 - 250300	17612	6	688905	2025-10-10 20:16:11	394046566608
15217	2025-10-08	17612 - 250300	17612	6	688805	2025-10-10 20:16:11	394046576344
15218	2025-10-08	17612 - 250300	17612	6	688975	2025-10-10 20:16:11	394046576230
15219	2025-10-08	17612 - 250300	17612	2	688865	2025-10-10 20:16:11	394046577476
15220	2025-10-08	17612 - 250300	17612	1	688855	2025-10-10 20:16:11	394046575646
15221	2025-10-09	17612 - 250300	17612	3	689285	2025-10-10 20:16:11	394090414670
15222	2025-10-09	17612 - 250300	17612	1	689275	2025-10-10 20:16:11	394090412759
15223	2025-10-09	17914 - 250297	17914	1	689115	2025-10-10 20:16:11	394090412737
15224	2025-10-09	17914 - 250297	17914	1	689265	2025-10-10 20:16:11	394090412174
15225	2025-10-09	18795 - 11001	18795	1	689135	2025-10-10 20:16:11	394090412325
15226	2025-10-09	17612 - 250300	17612	6	689255	2025-10-10 20:16:11	394090406422
15227	2025-10-09	17612 - 250300	17612	1	689345	2025-10-10 20:16:11	394090410610
14339	2025-10-09	17612 - 250300	17612	3	100510	2025-10-09 20:49:12	394090406514
14341	2025-10-09	17612 - 250300	17612	1	100512	2025-10-09 20:49:12	394090408789
15230	2025-10-09	17612 - 250300	17612	1	689335	2025-10-10 20:16:11	394090409763
15231	2025-10-09	17612 - 250300	17612	6	689125	2025-10-10 20:16:11	394090404084
15232	2025-10-09	17904 - 250240	17904	1	689245	2025-10-10 20:16:11	394090408506
15233	2025-10-09	17612 - 250300	17612	15	689325	2025-10-10 20:16:11	394090395476
15234	2025-10-09	17612 - 250300	17612	1	689195	2025-10-10 20:16:11	394090408171
15235	2025-10-09	17612 - 250300	17612	15	689235	2025-10-10 20:16:11	394090393738
14338	2025-10-09	17612 - 250300	17612	6	100509	2025-10-09 20:49:12	394090402427
15237	2025-10-09	17612 - 250300	17612	6	689185	2025-10-10 20:16:11	394090400906
14342	2025-10-09	17612 - 250300	17612	15	100513	2025-10-09 20:49:12	394090391595
15239	2025-10-09	17612 - 250300	17612	2	689115	2025-10-10 20:16:11	394090401177
15240	2025-10-09	17914 - 250297	17914	2	689105	2025-10-10 20:16:11	394090399379
15241	2025-10-09	17612 - 250300	17612	2	689155	2025-10-10 20:16:11	394090399449
14340	2025-10-09	17914 - 250297	17914	1	100511	2025-10-09 20:49:12	394090400939
15243	2025-10-09	17612 - 250300	17612	3	689175	2025-10-10 20:16:11	394090397722
15244	2025-10-09	17612 - 250300	17612	6	689145	2025-10-10 20:16:11	394090394414
15245	2025-10-09	17612 - 250300	17612	6	689095	2025-10-10 20:16:11	394090394583
15246	2025-10-09	17612 - 250300	17612	6	689165	2025-10-10 20:16:11	394090392558
16196	2025-10-09	17612 - 250300	17612	2	100514	2025-10-10 20:18:36	394090392628
15248	2025-10-09	17612 - 250300	17612	1	689225	2025-10-10 20:16:11	394090392639
15249	2025-10-09	17612 - 250300	17612	2	689135	2025-10-10 20:16:11	394090392488
15250	2025-10-09	17612 - 250300	17612	2	689085	2025-10-10 20:16:11	394090391507
15251	2025-10-09	17904 - 250240	17904	1	689315	2025-10-10 20:16:11	394090389600
15252	2025-10-09	17612 - 250300	17612	1	689205	2025-10-10 20:16:11	394090391600
16197	2025-10-09	17612 - 250300	17612	1	100518	2025-10-10 20:18:36	394095397106
14347	2025-10-09	17612 - 250300	17612	5	100521	2025-10-09 20:49:12	394095398981
14349	2025-10-09	17914 - 250297	17914	2	100523	2025-10-09 20:49:12	394095400654
16201	2025-10-09	17612 - 250300	17612	2	100520	2025-10-13 19:52:04	394095399360
14348	2025-10-09	17612 - 250300	17612	1	100522	2025-10-09 20:49:12	394095400518
14345	2025-10-09	17612 - 250300	17612	2	100519	2025-10-09 20:49:12	394095397816
15259	2025-10-10	17612 - 250300	17612	4	689405	2025-10-10 20:16:11	394131349275
15260	2025-10-10	17612 - 250300	17612	8	100516	2025-10-10 20:16:11	394131342980
15261	2025-10-10	17612 - 250300	17612	15	689395	2025-10-10 20:16:11	394131332729
15262	2025-10-10	17612 - 250300	17612	10	100515	2025-10-10 20:16:11	394131334136
15263	2025-10-10	17612 - 250300	17612	6	689455	2025-10-10 20:16:11	394131335669
15264	2025-10-10	17612 - 250300	17612	1	689385	2025-10-10 20:16:11	394131339631
16200	2025-10-10	17612 - 250300	17612	2	100525	2025-10-10 20:18:36	394131336985
15266	2025-10-10	17612 - 250300	17612	6	100517	2025-10-10 20:16:11	394131334331
16199	2025-10-10	17612 - 250300	17612	1	100524	2025-10-10 20:18:36	394131334401
15268	2025-10-10	17914 - 250297	17914	1	689425	2025-10-10 20:16:11	394131333416
15269	2025-10-10	17904 - 250240	17904	1	689435	2025-10-10 20:16:11	394131335257
15270	2025-10-10	17612 - 250300	17612	1	689435	2025-10-10 20:16:11	394131332317
15271	2025-10-10	17612 - 250300	17612	1	689415	2025-10-10 20:16:11	394131333677
15272	2025-10-10	17612 - 250300	17612	1	689465	2025-10-10 20:16:11	394131333953
17053	2025-10-13	17612 - 250300	17612	15	689495	2025-10-15 19:54:12.859575+00	394201122663
17054	2025-10-13	17612 - 250300	17612	3	689665	2025-10-15 19:54:12.859575+00	394201133958
16202	2025-10-13	17612 - 250300	17612	1	100526	2025-10-13 19:52:04	394201135413
17056	2025-10-13	17612 - 250300	17612	2	689655	2025-10-15 19:54:12.859575+00	394201132984
17057	2025-10-13	17612 - 250300	17612	6	689645	2025-10-15 19:54:12.859575+00	394201124942
17058	2025-10-13	17612 - 250300	17612	15	689635	2025-10-15 19:54:12.859575+00	394201104414
17059	2025-10-13	17612 - 250300	17612	15	689485	2025-10-15 19:54:12.859575+00	394201101713
17060	2025-10-13	17612 - 250300	17612	6	689565	2025-10-15 19:54:12.859575+00	394201113761
17061	2025-10-13	17612 - 250300	17612	6	689615	2025-10-15 19:54:12.859575+00	394201113257
17062	2025-10-13	17612 - 250300	17612	6	689515	2025-10-15 19:54:12.859575+00	394201103110
17063	2025-10-13	17612 - 250300	17612	6	689605	2025-10-15 19:54:12.859575+00	394201101724
17064	2025-10-13	17914 - 250297	17914	1	689515	2025-10-15 19:54:12.859575+00	394201105009
17065	2025-10-13	17904 - 250240	17904	1	689585	2025-10-15 19:54:12.859575+00	394201106060
17082	2025-10-14	17612 - 250300	17612	6	689925	2025-10-15 19:54:12.859575+00	394248568230
17083	2025-10-14	17612 - 250300	17612	2	689765	2025-10-15 19:54:12.859575+00	394248573950
17084	2025-10-14	17612 - 250300	17612	6	689755	2025-10-15 19:54:12.859575+00	394248567782
17085	2025-10-14	17612 - 250300	17612	1	689825	2025-10-15 19:54:12.859575+00	394248571465
17086	2025-10-14	17612 - 250300	17612	2	689815	2025-10-15 19:54:12.859575+00	394248569097
17087	2025-10-14	17612 - 250300	17612	1	689715	2025-10-15 19:54:12.859575+00	394248568263
17088	2025-10-14	17612 - 250300	17612	6	689695	2025-10-15 19:54:12.859575+00	394248561854
17089	2025-10-14	17612 - 250300	17612	6	689915	2025-10-15 19:54:12.859575+00	394248562129
17090	2025-10-14	17612 - 250300	17612	1	689795	2025-10-15 19:54:12.859575+00	394248567602
17091	2025-10-14	17612 - 250300	17612	6	689785	2025-10-15 19:54:12.859575+00	394248559751
17092	2025-10-14	17612 - 250300	17612	6	689745	2025-10-15 19:54:12.859575+00	394248560240
17093	2025-10-14	17612 - 250300	17612	6	689945	2025-10-15 19:54:12.859575+00	394248558836
17094	2025-10-14	17612 - 250300	17612	1	689885	2025-10-15 19:54:12.859575+00	394248562493
17095	2025-10-14	18795 - 11001	18795	2	689685	2025-10-15 19:54:12.859575+00	394248561361
17096	2025-10-14	17612 - 250300	17612	1	689865	2025-10-15 19:54:12.859575+00	394248560582
17097	2025-10-14	17612 - 250300	17612	2	689905	2025-10-15 19:54:12.859575+00	394248557737
17098	2025-10-14	17612 - 250300	17612	1	689855	2025-10-15 19:54:12.859575+00	394248558527
17099	2025-10-14	17612 - 250300	17612	1	689675	2025-10-15 19:54:12.859575+00	394248560446
17100	2025-10-15	17612 - 250300	17612	1	690205	2025-10-15 19:54:12.859575+00	394291930812
17101	2025-10-15	17612 - 250300	17612	2	690195	2025-10-15 19:54:12.859575+00	394291931955
17102	2025-10-15	17612 - 250300	17612	3	690185	2025-10-15 19:54:12.859575+00	394291927437
17103	2025-10-15	17612 - 250300	17612	2	690175	2025-10-15 19:54:12.859575+00	394291924563
17104	2025-10-15	18795 - 11001	18795	1	690165	2025-10-15 19:54:12.859575+00	394291920936
17105	2025-10-15	17612 - 250300	17612	1	690155	2025-10-15 19:54:12.859575+00	394291923545
17106	2025-10-15	17612 - 250300	17612	6	690145	2025-10-15 19:54:12.859575+00	394291918226
17107	2025-10-15	17612 - 250300	17612	6	690135	2025-10-15 19:54:12.859575+00	394291912191
17108	2025-10-15	17612 - 250300	17612	2	690115	2025-10-15 19:54:12.859575+00	394291908523
17109	2025-10-15	17914 - 250297	17914	1	690085	2025-10-15 19:54:12.859575+00	394291907516
17110	2025-10-15	17904 - 250240	17904	1	690075	2025-10-15 19:54:12.859575+00	394291905980
17111	2025-10-15	17904 - 250240	17904	6	690055	2025-10-15 19:54:12.859575+00	394291899087
17112	2025-10-15	17612 - 250300	17612	17	690045	2025-10-15 19:54:12.859575+00	394291884875
17113	2025-10-15	17612 - 250300	17612	1	690295	2025-10-15 19:54:12.859575+00	394291895931
17114	2025-10-15	17612 - 250300	17612	1	690285	2025-10-15 19:54:12.859575+00	394291895677
17115	2025-10-15	17612 - 250300	17612	1	690275	2025-10-15 19:54:12.859575+00	394291894019
17116	2025-10-15	17612 - 250300	17612	2	690265	2025-10-15 19:54:12.859575+00	394291888951
17117	2025-10-15	17612 - 250300	17612	1	690255	2025-10-15 19:54:12.859575+00	394291891579
17118	2025-10-15	17612 - 250300	17612	1	690245	2025-10-15 19:54:12.859575+00	394291889660
17119	2025-10-15	17612 - 250300	17612	3	690235	2025-10-15 19:54:12.859575+00	394291886948
17120	2025-10-15	17612 - 250300	17612	1	690225	2025-10-15 19:54:12.859575+00	394291885286
17121	2025-10-15	17612 - 250300	17612	1	690215	2025-10-15 19:54:12.859575+00	394291884268
17122	2025-10-15	18795 - 11001	18795	1	690035	2025-10-15 19:54:12.859575+00	394291884062
17123	2025-10-15	17612 - 250300	17612	1	100532	2025-10-15 19:54:12.859575+00	394291946936
17124	2025-10-15	17612 - 250300	17612	3	100531	2025-10-15 19:54:12.859575+00	394291943010
17125	2025-10-15	17612 - 250300	17612	8	100530	2025-10-15 19:54:12.859575+00	394291936497
17126	2025-10-15	17612 - 250300	17612	2	100529	2025-10-15 19:54:12.859575+00	394291933145
17127	2025-10-15	17612 - 250300	17612	2	100528	2025-10-15 19:54:12.859575+00	394291932859
17128	2025-10-15	17612 - 250300	17612	5	690625	2025-10-15 19:54:12.859575+00	394291927595
17129	2025-10-15	17612 - 250300	17612	11	100527	2025-10-15 19:54:12.859575+00	394291922652
17130	2025-10-15	17612 - 250300	17612	1	690615	2025-10-15 19:54:12.859575+00	394291926371
17131	2025-10-15	17612 - 250300	17612	1	690605	2025-10-15 19:54:12.859575+00	394291925592
17132	2025-10-15	17612 - 250300	17612	2	690485	2025-10-15 19:54:12.859575+00	394291923236
17133	2025-10-15	17914 - 250297	17914	1	690595	2025-10-15 19:54:12.859575+00	394291924736
17134	2025-10-15	17612 - 250300	17612	5	690585	2025-10-15 19:54:12.859575+00	394291920454
17135	2025-10-15	17612 - 250300	17612	6	690775	2025-10-15 19:54:12.859575+00	394291917860
17136	2025-10-15	17612 - 250300	17612	4	690475	2025-10-15 19:54:12.859575+00	394291919406
17137	2025-10-15	17612 - 250300	17612	1	690865	2025-10-15 19:54:12.859575+00	394291920605
17138	2025-10-15	17612 - 250300	17612	1	690075	2025-10-15 19:54:12.859575+00	394291917399
17139	2025-10-15	17612 - 250300	17612	5	690575	2025-10-15 19:54:12.859575+00	394291915043
17140	2025-10-15	17612 - 250300	17612	2	690465	2025-10-15 19:54:12.859575+00	394291917263
17141	2025-10-15	17612 - 250300	17612	4	690595	2025-10-15 19:54:12.859575+00	394291914908
17142	2025-10-15	17612 - 250300	17612	2	690765	2025-10-15 19:54:12.859575+00	394291916072
17143	2025-10-15	17612 - 250300	17612	1	690455	2025-10-15 19:54:12.859575+00	394291914838
17144	2025-10-15	17904 - 250240	17904	1	690745	2025-10-15 19:54:12.859575+00	394291913588
17145	2025-10-15	17612 - 250300	17612	1	690445	2025-10-15 19:54:12.859575+00	394291914610
17146	2025-10-15	17612 - 250300	17612	3	690735	2025-10-15 19:54:12.859575+00	394291911806
17147	2025-10-15	17612 - 250300	17612	10	690675	2025-10-15 19:54:12.859575+00	394291904024
17148	2025-10-15	17612 - 250300	17612	1	690435	2025-10-15 19:54:12.859575+00	394291913864
17149	2025-10-15	17612 - 250300	17612	1	690565	2025-10-15 19:54:12.859575+00	394291913419
17150	2025-10-15	17612 - 250300	17612	7	690425	2025-10-15 19:54:12.859575+00	394291906862
17151	2025-10-15	17612 - 250300	17612	10	690555	2025-10-15 19:54:12.859575+00	394291902433
17152	2025-10-15	17612 - 250300	17612	2	690725	2025-10-15 19:54:12.859575+00	394291908394
17153	2025-10-15	17904 - 250240	17904	1	690715	2025-10-15 19:54:12.859575+00	394291907181
17154	2025-10-15	17612 - 250300	17612	3	690345	2025-10-15 19:54:12.859575+00	394291903602
17155	2025-10-15	17612 - 250300	17612	1	690705	2025-10-15 19:54:12.859575+00	394291905237
17156	2025-10-15	17612 - 250300	17612	3	690415	2025-10-15 19:54:12.859575+00	394291903131
17158	2025-10-15	17612 - 250300	17612	4	690695	2025-10-15 19:54:12.859575+00	394291901665
17159	2025-10-15	17612 - 250300	17612	2	690335	2025-10-15 19:54:12.859575+00	394291901415
17160	2025-10-15	17612 - 250300	17612	2	690405	2025-10-15 19:54:12.859575+00	394291901161
17161	2025-10-15	17612 - 250300	17612	2	690545	2025-10-15 19:54:12.859575+00	394291901058
17162	2025-10-15	17612 - 250300	17612	2	690325	2025-10-15 19:54:12.859575+00	394291899640
17163	2025-10-15	17612 - 250300	17612	1	690685	2025-10-15 19:54:12.859575+00	394291900213
17164	2025-10-15	17612 - 250300	17612	1	690055	2025-10-15 19:54:12.859575+00	394291900511
17165	2025-10-15	17612 - 250300	17612	5	690395	2025-10-15 19:54:12.859575+00	394291895910
17166	2025-10-15	17612 - 250300	17612	3	690535	2025-10-15 19:54:12.859575+00	394291897912
17167	2025-10-15	17612 - 250300	17612	1	690855	2025-10-15 19:54:12.859575+00	394291898470
17168	2025-10-15	17914 - 250297	17914	1	690675	2025-10-15 19:54:12.859575+00	394291897794
17169	2025-10-15	17612 - 250300	17612	1	690315	2025-10-15 19:54:12.859575+00	394291898437
17170	2025-10-15	17612 - 250300	17612	6	690845	2025-10-15 19:54:12.859575+00	394291892748
17171	2025-10-15	17612 - 250300	17612	5	690665	2025-10-15 19:54:12.859575+00	394291893994
19148	2025-10-15	17612 - 250300	17612	6	688515	2025-10-15 21:09:53.675525+00	394302487109
\.


--
-- Data for Name: shipped_orders; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.shipped_orders (id, ship_date, order_number, customer_email, total_items, shipstation_order_id, created_at, shipping_carrier_code, shipping_carrier_id, shipping_service_code, shipping_service_name) FROM stdin;
1	2025-09-02	680165	\N	0	212461327	2025-10-01 12:22:31	\N	\N	\N	\N
2	2025-09-02	680305	\N	0	213498215	2025-10-01 12:22:31	\N	\N	\N	\N
3	2025-09-02	680205	\N	0	212495258	2025-10-01 12:22:31	\N	\N	\N	\N
4	2025-09-02	680175	\N	0	212473314	2025-10-01 12:22:31	\N	\N	\N	\N
5	2025-09-02	680315	\N	0	213500944	2025-10-01 12:22:31	\N	\N	\N	\N
6	2025-09-02	680255	\N	0	213441655	2025-10-01 12:22:31	\N	\N	\N	\N
7	2025-09-02	680225	\N	0	213143084	2025-10-01 12:22:31	\N	\N	\N	\N
8	2025-09-02	680275	\N	0	213456309	2025-10-01 12:22:31	\N	\N	\N	\N
10	2025-09-02	680325	\N	0	213510266	2025-10-01 12:22:31	\N	\N	\N	\N
11	2025-09-02	680235	\N	0	213181907	2025-10-01 12:22:31	\N	\N	\N	\N
12	2025-09-02	680245	\N	0	213390686	2025-10-01 12:22:31	\N	\N	\N	\N
13	2025-09-02	680335	\N	0	213510268	2025-10-01 12:22:31	\N	\N	\N	\N
14	2025-09-02	680285	\N	0	213471887	2025-10-01 12:22:31	\N	\N	\N	\N
15	2025-09-02	680345	\N	0	213510274	2025-10-01 12:22:31	\N	\N	\N	\N
16	2025-09-02	680355	\N	0	213512533	2025-10-01 12:22:31	\N	\N	\N	\N
17	2025-09-02	680365	\N	0	213514716	2025-10-01 12:22:31	\N	\N	\N	\N
18	2025-09-02	680375	\N	0	213516611	2025-10-01 12:22:31	\N	\N	\N	\N
19	2025-09-02	100468	\N	0	213483536	2025-10-01 12:22:31	\N	\N	\N	\N
20	2025-09-02	680295	\N	0	213484288	2025-10-01 12:22:31	\N	\N	\N	\N
21	2025-09-03	100469	\N	0	213546232	2025-10-01 12:22:31	\N	\N	\N	\N
22	2025-09-03	680475	\N	0	213602452	2025-10-01 12:22:31	\N	\N	\N	\N
23	2025-09-03	680425	\N	0	213572198	2025-10-01 12:22:31	\N	\N	\N	\N
24	2025-09-03	100470	\N	0	213813756	2025-10-01 12:22:31	\N	\N	\N	\N
25	2025-09-03	680485	\N	0	213605090	2025-10-01 12:22:31	\N	\N	\N	\N
26	2025-09-03	680435	\N	0	213578070	2025-10-01 12:22:31	\N	\N	\N	\N
27	2025-09-03	680515	\N	0	213627376	2025-10-01 12:22:31	\N	\N	\N	\N
28	2025-09-03	680495	\N	0	213617520	2025-10-01 12:22:31	\N	\N	\N	\N
29	2025-09-03	680385	\N	0	213816501	2025-10-01 12:22:31	\N	\N	\N	\N
30	2025-09-03	680445	\N	0	213583292	2025-10-01 12:22:31	\N	\N	\N	\N
31	2025-09-03	680395	\N	0	213546102	2025-10-01 12:22:31	\N	\N	\N	\N
32	2025-09-03	680525	\N	0	213792092	2025-10-01 12:22:31	\N	\N	\N	\N
34	2025-09-03	680455	\N	0	213588825	2025-10-01 12:22:31	\N	\N	\N	\N
36	2025-09-03	680405	\N	0	213546106	2025-10-01 12:22:31	\N	\N	\N	\N
37	2025-09-03	100471	\N	0	213823004	2025-10-01 12:22:31	\N	\N	\N	\N
38	2025-09-03	680465	\N	0	213594268	2025-10-01 12:22:31	\N	\N	\N	\N
39	2025-09-03	680535	\N	0	213792094	2025-10-01 12:22:31	\N	\N	\N	\N
40	2025-09-04	680575	\N	0	214126125	2025-10-01 12:22:31	\N	\N	\N	\N
41	2025-09-04	680955	\N	0	214137838	2025-10-01 12:22:31	\N	\N	\N	\N
42	2025-09-04	680735	\N	0	214126169	2025-10-01 12:22:31	\N	\N	\N	\N
43	2025-09-04	680905	\N	0	214126215	2025-10-01 12:22:31	\N	\N	\N	\N
44	2025-09-04	680745	\N	0	214126172	2025-10-01 12:22:31	\N	\N	\N	\N
45	2025-09-04	680965	\N	0	214142974	2025-10-01 12:22:31	\N	\N	\N	\N
46	2025-09-04	680755	\N	0	214126173	2025-10-01 12:22:31	\N	\N	\N	\N
47	2025-09-04	680975	\N	0	214158687	2025-10-01 12:22:31	\N	\N	\N	\N
48	2025-09-04	680815	\N	0	214126183	2025-10-01 12:22:31	\N	\N	\N	\N
49	2025-09-04	680915	\N	0	214126216	2025-10-01 12:22:31	\N	\N	\N	\N
50	2025-09-04	680785	\N	0	214126177	2025-10-01 12:22:31	\N	\N	\N	\N
51	2025-09-04	680825	\N	0	214126184	2025-10-01 12:22:31	\N	\N	\N	\N
52	2025-09-04	680585	\N	0	214126129	2025-10-01 12:22:31	\N	\N	\N	\N
54	2025-09-04	680795	\N	0	214126180	2025-10-01 12:22:31	\N	\N	\N	\N
55	2025-09-04	680595	\N	0	214126131	2025-10-01 12:22:31	\N	\N	\N	\N
56	2025-09-04	680805	\N	0	214126182	2025-10-01 12:22:31	\N	\N	\N	\N
57	2025-09-04	680985	\N	0	214153941	2025-10-01 12:22:31	\N	\N	\N	\N
58	2025-09-04	680605	\N	0	214126133	2025-10-01 12:22:31	\N	\N	\N	\N
59	2025-09-04	680925	\N	0	214137831	2025-10-01 12:22:31	\N	\N	\N	\N
60	2025-09-04	680995	\N	0	214156533	2025-10-01 12:22:31	\N	\N	\N	\N
61	2025-09-04	680935	\N	0	214137833	2025-10-01 12:22:31	\N	\N	\N	\N
63	2025-09-04	680835	\N	0	214126185	2025-10-01 12:22:31	\N	\N	\N	\N
64	2025-09-04	680645	\N	0	214126155	2025-10-01 12:22:31	\N	\N	\N	\N
65	2025-09-04	680945	\N	0	214137836	2025-10-01 12:22:31	\N	\N	\N	\N
66	2025-09-04	680875	\N	0	214126206	2025-10-01 12:22:31	\N	\N	\N	\N
68	2025-09-04	680655	\N	0	214126156	2025-10-01 12:22:31	\N	\N	\N	\N
69	2025-09-04	681015	\N	0	214161211	2025-10-01 12:22:31	\N	\N	\N	\N
70	2025-09-04	680615	\N	0	214126142	2025-10-01 12:22:31	\N	\N	\N	\N
71	2025-09-04	681025	\N	0	214166054	2025-10-01 12:22:31	\N	\N	\N	\N
72	2025-09-04	100472	\N	0	214184410	2025-10-01 12:22:31	\N	\N	\N	\N
73	2025-09-04	680885	\N	0	214126209	2025-10-01 12:22:31	\N	\N	\N	\N
74	2025-09-04	680665	\N	0	214126159	2025-10-01 12:22:31	\N	\N	\N	\N
75	2025-09-04	681035	\N	0	214185312	2025-10-01 12:22:31	\N	\N	\N	\N
76	2025-09-04	680895	\N	0	214126210	2025-10-01 12:22:31	\N	\N	\N	\N
77	2025-09-04	680625	\N	0	214126148	2025-10-01 12:22:31	\N	\N	\N	\N
78	2025-09-04	680675	\N	0	214126160	2025-10-01 12:22:31	\N	\N	\N	\N
79	2025-09-04	680695	\N	0	214126166	2025-10-01 12:22:31	\N	\N	\N	\N
80	2025-09-04	680725	\N	0	214126168	2025-10-01 12:22:31	\N	\N	\N	\N
421	2025-09-17	100490	\N	0	217593100	2025-10-01 12:22:31	\N	\N	\N	\N
727	2025-08-26	100464	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
636	2025-09-26	686495	\N	0	219909074	2025-10-01 12:22:31	\N	\N	\N	\N
658	2025-08-22	678565	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
659	2025-08-22	675355	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
660	2025-08-22	671825	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
661	2025-08-22	678625	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
662	2025-08-22	678575	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
663	2025-08-22	678585	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
664	2025-08-22	678595	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
665	2025-08-22	674715	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
666	2025-08-22	673125	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
667	2025-08-22	675975	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
668	2025-08-22	678645	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
669	2025-08-22	678635	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
670	2025-08-22	678615	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
671	2025-08-22	678665	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
672	2025-08-22	678655	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
673	2025-08-22	678605	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
674	2025-08-25	678925	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
675	2025-08-25	678945	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
676	2025-08-25	679035	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
677	2025-08-25	679095	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
678	2025-08-25	678935	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
679	2025-08-25	678865	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
680	2025-08-25	678815	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
681	2025-08-25	679085	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
682	2025-08-25	679025	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
683	2025-08-25	679005	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
684	2025-08-25	678675	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
685	2025-08-25	678855	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
686	2025-08-25	678845	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
687	2025-08-25	679075	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
688	2025-08-25	679065	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
689	2025-08-25	678765	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
690	2025-08-25	678685	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
691	2025-08-25	678755	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
692	2025-08-25	678995	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
693	2025-08-25	679015	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
694	2025-08-25	678955	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
695	2025-08-25	678785	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
696	2025-08-25	678705	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
697	2025-08-25	678795	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
698	2025-08-25	100462	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
699	2025-08-25	678915	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
700	2025-08-25	100463	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
701	2025-08-25	678885	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
702	2025-08-25	679125	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
703	2025-08-25	679055	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
704	2025-08-25	678985	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
705	2025-08-25	679115	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
706	2025-08-25	678895	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
707	2025-08-25	679045	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
708	2025-08-25	678835	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
709	2025-08-25	678975	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
710	2025-08-25	679105	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
711	2025-08-25	678875	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
712	2025-08-25	678725	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
713	2025-08-25	678965	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
714	2025-08-25	678715	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
715	2025-08-25	678825	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
716	2025-08-25	678735	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
717	2025-08-26	679165	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
718	2025-08-26	679185	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
719	2025-08-26	679325	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
720	2025-08-26	679155	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
721	2025-08-26	679395	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
722	2025-08-26	679385	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
723	2025-08-26	679145	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
724	2025-08-26	679235	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
725	2025-08-26	679315	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
726	2025-08-26	679175	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
728	2025-08-26	679375	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
729	2025-08-26	679335	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
730	2025-08-26	679365	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
731	2025-08-26	679245	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
732	2025-08-26	679415	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
733	2025-08-26	679425	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
734	2025-08-26	679345	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
735	2025-08-26	679255	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
736	2025-08-26	679135	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
737	2025-08-26	679445	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
738	2025-08-26	679215	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
739	2025-08-26	679225	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
740	2025-08-26	679435	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
741	2025-08-26	679305	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
742	2025-08-26	679205	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
743	2025-08-26	679285	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
744	2025-08-26	679195	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
745	2025-08-26	100466	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
746	2025-08-26	679355	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
747	2025-08-26	679265	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
748	2025-08-26	100465	\N	0	211474875	2025-10-01 13:49:27	\N	\N	\N	\N
749	2025-08-26	679295	\N	0	\N	2025-10-01 13:49:27	\N	\N	\N	\N
750	2025-08-27	679755	\N	0	211833007	2025-10-01 13:49:27	\N	\N	\N	\N
751	2025-08-27	679785	\N	0	211847521	2025-10-01 13:49:27	\N	\N	\N	\N
752	2025-08-27	679775	\N	0	211840482	2025-10-01 13:49:27	\N	\N	\N	\N
753	2025-08-27	679685	\N	0	211790069	2025-10-01 13:49:27	\N	\N	\N	\N
754	2025-08-27	679765	\N	0	211836125	2025-10-01 13:49:27	\N	\N	\N	\N
755	2025-08-27	679565	\N	0	211624805	2025-10-01 13:49:27	\N	\N	\N	\N
756	2025-08-27	679555	\N	0	211624799	2025-10-01 13:49:27	\N	\N	\N	\N
757	2025-08-27	679625	\N	0	211662001	2025-10-01 13:49:27	\N	\N	\N	\N
758	2025-08-27	679615	\N	0	211661999	2025-10-01 13:49:27	\N	\N	\N	\N
759	2025-08-27	679745	\N	0	211823837	2025-10-01 13:49:27	\N	\N	\N	\N
760	2025-08-27	679605	\N	0	211661997	2025-10-01 13:49:27	\N	\N	\N	\N
761	2025-08-27	679725	\N	0	211808025	2025-10-01 13:49:27	\N	\N	\N	\N
762	2025-08-27	679545	\N	0	211624795	2025-10-01 13:49:27	\N	\N	\N	\N
763	2025-08-27	679665	\N	0	211779188	2025-10-01 13:49:27	\N	\N	\N	\N
764	2025-08-27	679675	\N	0	211784200	2025-10-01 13:49:27	\N	\N	\N	\N
765	2025-08-27	679455	\N	0	211855545	2025-10-01 13:49:27	\N	\N	\N	\N
766	2025-08-27	679585	\N	0	211629471	2025-10-01 13:49:27	\N	\N	\N	\N
767	2025-08-27	679575	\N	0	211626947	2025-10-01 13:49:27	\N	\N	\N	\N
768	2025-08-27	679655	\N	0	211855465	2025-10-01 13:49:27	\N	\N	\N	\N
769	2025-08-27	679485	\N	0	211855374	2025-10-01 13:49:27	\N	\N	\N	\N
770	2025-08-27	679535	\N	0	211621098	2025-10-01 13:49:27	\N	\N	\N	\N
771	2025-08-27	679805	\N	0	211862495	2025-10-01 13:49:27	\N	\N	\N	\N
772	2025-08-27	679505	\N	0	211605638	2025-10-01 13:49:27	\N	\N	\N	\N
773	2025-08-27	679815	\N	0	211859353	2025-10-01 13:49:27	\N	\N	\N	\N
774	2025-08-27	679495	\N	0	211603680	2025-10-01 13:49:27	\N	\N	\N	\N
775	2025-08-27	679735	\N	0	211819709	2025-10-01 13:49:27	\N	\N	\N	\N
776	2025-08-27	679465	\N	0	211598655	2025-10-01 13:49:27	\N	\N	\N	\N
777	2025-08-27	679705	\N	0	211806298	2025-10-01 13:49:27	\N	\N	\N	\N
778	2025-08-27	679595	\N	0	211661990	2025-10-01 13:49:27	\N	\N	\N	\N
779	2025-08-27	679695	\N	0	211791123	2025-10-01 13:49:27	\N	\N	\N	\N
780	2025-08-27	679635	\N	0	211770089	2025-10-01 13:49:27	\N	\N	\N	\N
781	2025-08-27	679645	\N	0	211770092	2025-10-01 13:49:27	\N	\N	\N	\N
782	2025-08-27	679715	\N	0	211806302	2025-10-01 13:49:27	\N	\N	\N	\N
783	2025-08-28	680015	\N	0	212108228	2025-10-01 13:49:27	\N	\N	\N	\N
784	2025-08-28	679835	\N	0	211873650	2025-10-01 13:49:27	\N	\N	\N	\N
785	2025-08-28	679945	\N	0	212056800	2025-10-01 13:49:27	\N	\N	\N	\N
786	2025-08-28	679915	\N	0	212056797	2025-10-01 13:49:27	\N	\N	\N	\N
787	2025-08-28	679905	\N	0	211911738	2025-10-01 13:49:27	\N	\N	\N	\N
788	2025-08-28	680085	\N	0	212168655	2025-10-01 13:49:27	\N	\N	\N	\N
789	2025-08-28	679795	\N	0	211851891	2025-10-01 13:49:27	\N	\N	\N	\N
790	2025-08-28	679515	\N	0	211610608	2025-10-01 13:49:27	\N	\N	\N	\N
791	2025-08-28	680075	\N	0	212165442	2025-10-01 13:49:27	\N	\N	\N	\N
792	2025-08-28	679955	\N	0	212056803	2025-10-01 13:49:27	\N	\N	\N	\N
793	2025-08-28	679965	\N	0	212087931	2025-10-01 13:49:27	\N	\N	\N	\N
794	2025-08-28	679865	\N	0	211889639	2025-10-01 13:49:27	\N	\N	\N	\N
795	2025-08-28	679975	\N	0	212092048	2025-10-01 13:49:27	\N	\N	\N	\N
796	2025-08-28	679875	\N	0	211892235	2025-10-01 13:49:27	\N	\N	\N	\N
797	2025-08-28	679995	\N	0	212097478	2025-10-01 13:49:27	\N	\N	\N	\N
798	2025-08-28	679845	\N	0	211876399	2025-10-01 13:49:27	\N	\N	\N	\N
799	2025-08-28	680005	\N	0	212106645	2025-10-01 13:49:27	\N	\N	\N	\N
800	2025-08-28	680065	\N	0	212148640	2025-10-01 13:49:27	\N	\N	\N	\N
801	2025-08-28	679885	\N	0	211901425	2025-10-01 13:49:27	\N	\N	\N	\N
802	2025-08-28	679895	\N	0	211907623	2025-10-01 13:49:27	\N	\N	\N	\N
803	2025-08-28	680035	\N	0	212111117	2025-10-01 13:49:27	\N	\N	\N	\N
804	2025-08-28	680045	\N	0	212119332	2025-10-01 13:49:27	\N	\N	\N	\N
805	2025-08-28	679855	\N	0	211879297	2025-10-01 13:49:27	\N	\N	\N	\N
806	2025-08-28	680055	\N	0	212125416	2025-10-01 13:49:27	\N	\N	\N	\N
807	2025-08-28	679825	\N	0	211870361	2025-10-01 13:49:27	\N	\N	\N	\N
808	2025-08-29	680115	\N	0	212355415	2025-10-01 13:49:27	\N	\N	\N	\N
809	2025-08-29	680135	\N	0	212395329	2025-10-01 13:49:27	\N	\N	\N	\N
810	2025-08-29	680105	\N	0	212200171	2025-10-01 13:49:27	\N	\N	\N	\N
811	2025-08-29	100467	\N	0	212410430	2025-10-01 13:49:27	\N	\N	\N	\N
812	2025-08-29	680145	\N	0	212396555	2025-10-01 13:49:27	\N	\N	\N	\N
813	2025-08-29	680155	\N	0	212433143	2025-10-01 13:49:27	\N	\N	\N	\N
814	2025-08-29	680095	\N	0	212195570	2025-10-01 13:49:27	\N	\N	\N	\N
4684	2024-04-16	686865	\N	0	66552503	2025-10-02 20:53:07	fedex	556346	fedex_ground	FedEx Ground
4685	2024-04-16	686855	\N	0	66552503	2025-10-02 20:53:07	fedex	556346	fedex_ground	FedEx Ground
4686	2024-04-16	686625	\N	0	66552503	2025-10-02 20:53:07	fedex	556346	fedex_ground	FedEx Ground
4687	2024-04-16	686615	\N	0	66552503	2025-10-02 20:53:08	fedex	556346	fedex_ground	FedEx Ground
4711	2024-04-16	687915	\N	0	66552503	2025-10-03 17:19:28	fedex	556346	fedex_ground	FedEx Ground
4712	2024-04-16	687905	\N	0	66552503	2025-10-03 17:19:29	fedex	556346	fedex_ground	FedEx Ground
4713	2024-04-16	687895	\N	0	66552503	2025-10-03 17:19:29	fedex	556346	fedex_ground	FedEx Ground
12344	2025-06-24	665745	\N	0	191568586	2025-10-07 05:01:48	\N	\N	\N	\N
4692	2025-10-03	687855	\N	0	221735760	2025-10-03 13:50:58	fedex	556346	fedex_ground	FedEx Ground
13054	2025-10-07	688315	\N	0	222405850	2025-10-10 20:16:10	\N	\N	\N	\N
109	2025-09-05	681565	\N	0	214441578	2025-10-01 12:22:31	\N	\N	\N	\N
108	2025-09-05	681705	\N	0	214451188	2025-10-01 12:22:31	\N	\N	\N	\N
14052	2024-05-21	100032	\N	0	76606327	2025-10-14 17:41:55	\N	\N	\N	\N
14067	2024-11-13	100196	\N	0	123457213	2025-10-15 05:23:36.295358+00	\N	\N	\N	\N
107	2025-09-05	681235	\N	0	214438516	2025-10-01 12:22:31	\N	\N	\N	\N
106	2025-09-05	681555	\N	0	214441575	2025-10-01 12:22:31	\N	\N	\N	\N
105	2025-09-05	681055	\N	0	214189515	2025-10-01 12:22:31	\N	\N	\N	\N
14068	2024-11-13	100197	\N	0	123459251	2025-10-15 05:23:36.295358+00	\N	\N	\N	\N
14069	2024-11-13	100198	\N	0	123459638	2025-10-15 05:23:36.295358+00	\N	\N	\N	\N
104	2025-09-05	681685	\N	0	214449402	2025-10-01 12:22:31	\N	\N	\N	\N
103	2025-09-05	681545	\N	0	214441570	2025-10-01 12:22:31	\N	\N	\N	\N
102	2025-09-05	681665	\N	0	214448468	2025-10-01 12:22:31	\N	\N	\N	\N
14051	2025-07-16	100428	\N	0	199213209	2025-10-14 17:17:53	\N	\N	\N	\N
101	2025-09-05	681335	\N	0	214439252	2025-10-01 12:22:31	\N	\N	\N	\N
100	2025-09-05	681405	\N	0	214440171	2025-10-01 12:22:31	\N	\N	\N	\N
99	2025-09-05	681655	\N	0	214442749	2025-10-01 12:22:31	\N	\N	\N	\N
98	2025-09-05	681325	\N	0	214439251	2025-10-01 12:22:31	\N	\N	\N	\N
97	2025-09-05	681645	\N	0	214442746	2025-10-01 12:22:31	\N	\N	\N	\N
13140	2025-10-08	688995	\N	0	223038626	2025-10-10 20:16:10	\N	\N	\N	\N
13134	2025-10-08	688975	\N	0	223023369	2025-10-10 20:16:10	\N	\N	\N	\N
13135	2025-10-08	688865	\N	0	222840207	2025-10-10 20:16:10	\N	\N	\N	\N
13194	2025-10-10	100524	\N	0	223770760	2025-10-10 20:16:10	\N	\N	\N	\N
14887	2025-10-15	690545	\N	0	225005526	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14888	2025-10-15	690405	\N	0	225003326	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14900	2025-10-15	690735	\N	0	225007528	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14893	2025-10-15	690565	\N	0	225005533	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14898	2025-10-15	690435	\N	0	225004497	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14899	2025-10-15	690675	\N	0	225060528	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14903	2025-10-15	690395	\N	0	225003324	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14892	2025-10-15	690705	\N	0	225006655	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14914	2025-10-15	690535	\N	0	225005523	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14909	2025-10-15	690495	\N	0	225004513	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14923	2025-10-15	690315	\N	0	225001916	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14889	2025-10-15	690335	\N	0	225001922	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14886	2025-10-15	690415	\N	0	225003328	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14897	2025-10-15	690425	\N	0	225003334	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14902	2025-10-15	690345	\N	0	225001924	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14894	2025-10-15	690715	\N	0	225007523	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14895	2025-10-15	690725	\N	0	225007525	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14896	2025-10-15	690555	\N	0	225005528	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
379	2025-09-16	683855	\N	0	217017642	2025-10-01 12:22:31	\N	\N	\N	\N
148	2025-09-08	100473	\N	0	215172613	2025-10-01 12:22:31	\N	\N	\N	\N
13052	2025-10-07	687965	\N	0	222400691	2025-10-10 20:16:10	\N	\N	\N	\N
110	2025-09-05	681245	\N	0	214438517	2025-10-01 12:22:31	\N	\N	\N	\N
96	2025-09-05	681535	\N	0	214441568	2025-10-01 12:22:31	\N	\N	\N	\N
94	2025-09-05	681525	\N	0	214440846	2025-10-01 12:22:31	\N	\N	\N	\N
93	2025-09-05	681205	\N	0	214437899	2025-10-01 12:22:31	\N	\N	\N	\N
92	2025-09-05	681305	\N	0	214438534	2025-10-01 12:22:31	\N	\N	\N	\N
91	2025-09-05	681515	\N	0	214440837	2025-10-01 12:22:31	\N	\N	\N	\N
90	2025-09-05	681195	\N	0	214437897	2025-10-01 12:22:31	\N	\N	\N	\N
89	2025-09-05	681635	\N	0	214442744	2025-10-01 12:22:31	\N	\N	\N	\N
87	2025-09-05	681295	\N	0	214438530	2025-10-01 12:22:31	\N	\N	\N	\N
86	2025-09-05	681625	\N	0	214442741	2025-10-01 12:22:31	\N	\N	\N	\N
85	2025-09-05	681175	\N	0	214437894	2025-10-01 12:22:31	\N	\N	\N	\N
84	2025-09-05	681395	\N	0	214440169	2025-10-01 12:22:31	\N	\N	\N	\N
83	2025-09-05	681285	\N	0	214438528	2025-10-01 12:22:31	\N	\N	\N	\N
82	2025-09-05	681165	\N	0	214437892	2025-10-01 12:22:31	\N	\N	\N	\N
145	2025-09-05	681155	\N	0	214504468	2025-10-01 12:22:31	\N	\N	\N	\N
95	2025-09-05	681315	\N	0	214438535	2025-10-01 12:22:31	\N	\N	\N	\N
111	2025-09-05	681725	\N	0	214459840	2025-10-01 12:22:31	\N	\N	\N	\N
88	2025-09-05	681185	\N	0	214437895	2025-10-01 12:22:31	\N	\N	\N	\N
113	2025-09-05	681345	\N	0	214439254	2025-10-01 12:22:31	\N	\N	\N	\N
112	2025-09-05	681425	\N	0	214440172	2025-10-01 12:22:31	\N	\N	\N	\N
144	2025-09-05	681145	\N	0	214430075	2025-10-01 12:22:31	\N	\N	\N	\N
143	2025-09-05	681135	\N	0	214430074	2025-10-01 12:22:31	\N	\N	\N	\N
142	2025-09-05	681125	\N	0	214430073	2025-10-01 12:22:31	\N	\N	\N	\N
141	2025-09-05	681505	\N	0	214440833	2025-10-01 12:22:31	\N	\N	\N	\N
140	2025-09-05	681115	\N	0	214430072	2025-10-01 12:22:31	\N	\N	\N	\N
139	2025-09-05	681615	\N	0	214441583	2025-10-01 12:22:31	\N	\N	\N	\N
119	2025-09-05	681105	\N	0	214224069	2025-10-01 12:22:31	\N	\N	\N	\N
137	2025-09-05	681605	\N	0	214441582	2025-10-01 12:22:31	\N	\N	\N	\N
135	2025-09-05	681485	\N	0	214440827	2025-10-01 12:22:31	\N	\N	\N	\N
134	2025-09-05	681385	\N	0	214439258	2025-10-01 12:22:31	\N	\N	\N	\N
13179	2025-10-09	689265	\N	0	223293231	2025-10-10 20:16:10	\N	\N	\N	\N
67	2025-09-05	681005	\N	0	214177975	2025-10-01 12:22:31	\N	\N	\N	\N
133	2025-09-05	681095	\N	0	214221547	2025-10-01 12:22:31	\N	\N	\N	\N
132	2025-09-05	681475	\N	0	214440824	2025-10-01 12:22:31	\N	\N	\N	\N
131	2025-09-05	681465	\N	0	214440823	2025-10-01 12:22:31	\N	\N	\N	\N
136	2025-09-05	681495	\N	0	214440831	2025-10-01 12:22:31	\N	\N	\N	\N
129	2025-09-05	681455	\N	0	214440820	2025-10-01 12:22:31	\N	\N	\N	\N
114	2025-09-05	681255	\N	0	214438519	2025-10-01 12:22:31	\N	\N	\N	\N
115	2025-09-05	681435	\N	0	214440178	2025-10-01 12:22:31	\N	\N	\N	\N
130	2025-09-05	681085	\N	0	214215407	2025-10-01 12:22:31	\N	\N	\N	\N
117	2025-09-05	681445	\N	0	214440818	2025-10-01 12:22:31	\N	\N	\N	\N
118	2025-09-05	681355	\N	0	214439255	2025-10-01 12:22:31	\N	\N	\N	\N
120	2025-09-05	681575	\N	0	214441579	2025-10-01 12:22:31	\N	\N	\N	\N
121	2025-09-05	681065	\N	0	214193095	2025-10-01 12:22:31	\N	\N	\N	\N
116	2025-09-05	681265	\N	0	214438520	2025-10-01 12:22:31	\N	\N	\N	\N
124	2025-09-05	681365	\N	0	214439256	2025-10-01 12:22:31	\N	\N	\N	\N
125	2025-09-05	681585	\N	0	214441580	2025-10-01 12:22:31	\N	\N	\N	\N
126	2025-09-05	681075	\N	0	214210205	2025-10-01 12:22:31	\N	\N	\N	\N
127	2025-09-05	681375	\N	0	214439257	2025-10-01 12:22:31	\N	\N	\N	\N
128	2025-09-05	681595	\N	0	214441581	2025-10-01 12:22:31	\N	\N	\N	\N
122	2025-09-05	681275	\N	0	214438522	2025-10-01 12:22:31	\N	\N	\N	\N
158	2025-09-08	681865	\N	0	215155323	2025-10-01 12:22:31	\N	\N	\N	\N
157	2025-09-08	681805	\N	0	214577185	2025-10-01 12:22:31	\N	\N	\N	\N
156	2025-09-08	681775	\N	0	214551168	2025-10-01 12:22:31	\N	\N	\N	\N
155	2025-09-08	681895	\N	0	215161690	2025-10-01 12:22:31	\N	\N	\N	\N
152	2025-09-08	681825	\N	0	215135114	2025-10-01 12:22:31	\N	\N	\N	\N
153	2025-09-08	681855	\N	0	215147923	2025-10-01 12:22:31	\N	\N	\N	\N
151	2025-09-08	681745	\N	0	214551165	2025-10-01 12:22:31	\N	\N	\N	\N
149	2025-09-08	681945	\N	0	215177876	2025-10-01 12:22:31	\N	\N	\N	\N
159	2025-09-08	681955	\N	0	215189569	2025-10-01 12:22:31	\N	\N	\N	\N
154	2025-09-08	681965	\N	0	215207013	2025-10-01 12:22:31	\N	\N	\N	\N
150	2025-09-08	681815	\N	0	215206923	2025-10-01 12:22:31	\N	\N	\N	\N
165	2025-09-08	681845	\N	0	215145444	2025-10-01 12:22:31	\N	\N	\N	\N
163	2025-09-08	681835	\N	0	215136309	2025-10-01 12:22:31	\N	\N	\N	\N
147	2025-09-08	681735	\N	0	214551163	2025-10-01 12:22:31	\N	\N	\N	\N
171	2025-09-08	681995	\N	0	215225245	2025-10-01 12:22:31	\N	\N	\N	\N
170	2025-09-08	681925	\N	0	215168969	2025-10-01 12:22:31	\N	\N	\N	\N
169	2025-09-08	681915	\N	0	215168967	2025-10-01 12:22:31	\N	\N	\N	\N
160	2025-09-08	681975	\N	0	215228748	2025-10-01 12:22:31	\N	\N	\N	\N
167	2025-09-08	681885	\N	0	215160063	2025-10-01 12:22:31	\N	\N	\N	\N
166	2025-09-08	681985	\N	0	215216172	2025-10-01 12:22:31	\N	\N	\N	\N
164	2025-09-08	681905	\N	0	215164388	2025-10-01 12:22:31	\N	\N	\N	\N
168	2025-09-08	100474	\N	0	215218487	2025-10-01 12:22:31	\N	\N	\N	\N
162	2025-09-08	681875	\N	0	215155326	2025-10-01 12:22:31	\N	\N	\N	\N
179	2025-09-09	682065	\N	0	215295254	2025-10-01 12:22:31	\N	\N	\N	\N
173	2025-09-09	682035	\N	0	215253714	2025-10-01 12:22:31	\N	\N	\N	\N
174	2025-09-09	682095	\N	0	215447386	2025-10-01 12:22:31	\N	\N	\N	\N
175	2025-09-09	682005	\N	0	215235143	2025-10-01 12:22:31	\N	\N	\N	\N
176	2025-09-09	682125	\N	0	215460875	2025-10-01 12:22:31	\N	\N	\N	\N
177	2025-09-09	682045	\N	0	215270202	2025-10-01 12:22:31	\N	\N	\N	\N
178	2025-09-09	682025	\N	0	215252065	2025-10-01 12:22:31	\N	\N	\N	\N
180	2025-09-09	682155	\N	0	215516301	2025-10-01 12:22:31	\N	\N	\N	\N
182	2025-09-09	682085	\N	0	215317007	2025-10-01 12:22:31	\N	\N	\N	\N
183	2025-09-09	100476	\N	0	215527972	2025-10-01 12:22:31	\N	\N	\N	\N
184	2025-09-09	682135	\N	0	215465964	2025-10-01 12:22:31	\N	\N	\N	\N
185	2025-09-09	100475	\N	0	215533828	2025-10-01 12:22:31	\N	\N	\N	\N
186	2025-09-09	682145	\N	0	215485889	2025-10-01 12:22:31	\N	\N	\N	\N
181	2025-09-09	682175	\N	0	215527199	2025-10-01 12:22:31	\N	\N	\N	\N
197	2025-09-10	100477	\N	0	215606057	2025-10-01 12:22:31	\N	\N	\N	\N
196	2025-09-10	682335	\N	0	215770154	2025-10-01 12:22:31	\N	\N	\N	\N
195	2025-09-10	682305	\N	0	215744667	2025-10-01 12:22:31	\N	\N	\N	\N
194	2025-09-10	682275	\N	0	215724430	2025-10-01 12:22:31	\N	\N	\N	\N
190	2025-09-10	682395	\N	0	215810198	2025-10-01 12:22:31	\N	\N	\N	\N
191	2025-09-10	682225	\N	0	215595962	2025-10-01 12:22:31	\N	\N	\N	\N
14960	2025-10-15	100528	\N	0	225073041	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14961	2025-10-15	100529	\N	0	225073050	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14962	2025-10-15	100531	\N	0	225073068	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14963	2025-10-15	100532	\N	0	225073075	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14964	2025-10-15	690035	\N	0	224812328	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14965	2025-10-15	690215	\N	0	224999421	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14958	2025-10-15	690615	\N	0	225005543	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
10704	2025-10-15	688515	\N	0	222700937	2025-10-06 18:45:12	fedex	556346	fedex_ground	FedEx Ground
188	2025-09-10	682385	\N	0	215796571	2025-10-01 12:22:31	\N	\N	\N	\N
187	2025-09-10	682255	\N	0	215716500	2025-10-01 12:22:31	\N	\N	\N	\N
198	2025-09-10	682315	\N	0	215745592	2025-10-01 12:22:31	\N	\N	\N	\N
193	2025-09-10	682265	\N	0	215723816	2025-10-01 12:22:31	\N	\N	\N	\N
199	2025-09-10	682205	\N	0	215581482	2025-10-01 12:22:31	\N	\N	\N	\N
201	2025-09-10	682215	\N	0	215589931	2025-10-01 12:22:31	\N	\N	\N	\N
200	2025-09-10	682405	\N	0	215812066	2025-10-01 12:22:31	\N	\N	\N	\N
202	2025-09-10	682235	\N	0	215716498	2025-10-01 12:22:31	\N	\N	\N	\N
203	2025-09-10	682415	\N	0	215819040	2025-10-01 12:22:31	\N	\N	\N	\N
204	2025-09-10	682295	\N	0	215744665	2025-10-01 12:22:31	\N	\N	\N	\N
205	2025-09-10	682345	\N	0	215787228	2025-10-01 12:22:31	\N	\N	\N	\N
192	2025-09-10	682195	\N	0	215748747	2025-10-01 12:22:31	\N	\N	\N	\N
207	2025-09-10	682325	\N	0	215767755	2025-10-01 12:22:31	\N	\N	\N	\N
208	2025-09-10	682355	\N	0	215788684	2025-10-01 12:22:31	\N	\N	\N	\N
209	2025-09-10	682365	\N	0	215790336	2025-10-01 12:22:31	\N	\N	\N	\N
210	2025-09-10	682245	\N	0	215716499	2025-10-01 12:22:31	\N	\N	\N	\N
189	2025-09-10	682185	\N	0	215562332	2025-10-01 12:22:31	\N	\N	\N	\N
220	2025-09-11	682455	\N	0	215845068	2025-10-01 12:22:31	\N	\N	\N	\N
219	2025-09-11	682595	\N	0	215895468	2025-10-01 12:22:31	\N	\N	\N	\N
218	2025-09-11	682695	\N	0	216051100	2025-10-01 12:22:31	\N	\N	\N	\N
217	2025-09-11	682645	\N	0	216021825	2025-10-01 12:22:31	\N	\N	\N	\N
216	2025-09-11	682515	\N	0	215867535	2025-10-01 12:22:31	\N	\N	\N	\N
237	2025-09-11	100478	\N	0	216059757	2025-10-01 12:22:31	\N	\N	\N	\N
214	2025-09-11	682505	\N	0	215861245	2025-10-01 12:22:31	\N	\N	\N	\N
213	2025-09-11	682545	\N	0	215874866	2025-10-01 12:22:31	\N	\N	\N	\N
212	2025-09-11	682495	\N	0	215859634	2025-10-01 12:22:31	\N	\N	\N	\N
211	2025-09-11	682445	\N	0	215843309	2025-10-01 12:22:31	\N	\N	\N	\N
222	2025-09-11	682565	\N	0	215885426	2025-10-01 12:22:31	\N	\N	\N	\N
215	2025-09-11	682585	\N	0	215890264	2025-10-01 12:22:31	fedex	556346	fedex_international_priority_express	Fedex International Priority Express
223	2025-09-11	682475	\N	0	215845076	2025-10-01 12:22:31	\N	\N	\N	\N
221	2025-09-11	682555	\N	0	215882922	2025-10-01 12:22:31	\N	\N	\N	\N
225	2025-09-11	682535	\N	0	215873507	2025-10-01 12:22:31	\N	\N	\N	\N
224	2025-09-11	682575	\N	0	215887804	2025-10-01 12:22:31	\N	\N	\N	\N
236	2025-09-11	682425	\N	0	216013346	2025-10-01 12:22:31	\N	\N	\N	\N
235	2025-09-11	682755	\N	0	216089127	2025-10-01 12:22:31	\N	\N	\N	\N
234	2025-09-11	682745	\N	0	216070129	2025-10-01 12:22:31	\N	\N	\N	\N
232	2025-09-11	682685	\N	0	216048305	2025-10-01 12:22:31	\N	\N	\N	\N
231	2025-09-11	682665	\N	0	216030106	2025-10-01 12:22:31	\N	\N	\N	\N
233	2025-09-11	682735	\N	0	216068803	2025-10-01 12:22:31	\N	\N	\N	\N
229	2025-09-11	682605	\N	0	216008262	2025-10-01 12:22:31	\N	\N	\N	\N
228	2025-09-11	682485	\N	0	215854788	2025-10-01 12:22:31	\N	\N	\N	\N
227	2025-09-11	682705	\N	0	216058072	2025-10-01 12:22:31	\N	\N	\N	\N
226	2025-09-11	682655	\N	0	216025241	2025-10-01 12:22:31	\N	\N	\N	\N
230	2025-09-11	682725	\N	0	216065200	2025-10-01 12:22:31	\N	\N	\N	\N
249	2025-09-12	682805	\N	0	216113710	2025-10-01 12:22:31	\N	\N	\N	\N
254	2025-09-12	682815	\N	0	216123483	2025-10-01 12:22:31	\N	\N	\N	\N
255	2025-09-12	682955	\N	0	216273165	2025-10-01 12:22:31	\N	\N	\N	\N
252	2025-09-12	682945	\N	0	216273164	2025-10-01 12:22:31	\N	\N	\N	\N
251	2025-09-12	682865	\N	0	216137860	2025-10-01 12:22:31	\N	\N	\N	\N
250	2025-09-12	681795	\N	0	214559755	2025-10-01 12:22:31	\N	\N	\N	\N
248	2025-09-12	682795	\N	0	216112414	2025-10-01 12:22:31	\N	\N	\N	\N
240	2025-09-12	100484	\N	0	216339034	2025-10-01 12:22:31	\N	\N	\N	\N
245	2025-09-12	681755	\N	0	214551167	2025-10-01 12:22:31	\N	\N	\N	\N
243	2025-09-12	682775	\N	0	216112412	2025-10-01 12:22:31	\N	\N	\N	\N
242	2025-09-12	682845	\N	0	216134465	2025-10-01 12:22:31	\N	\N	\N	\N
241	2025-09-12	682925	\N	0	216273162	2025-10-01 12:22:31	\N	\N	\N	\N
238	2025-09-12	682915	\N	0	216273160	2025-10-01 12:22:31	\N	\N	\N	\N
256	2025-09-12	682875	\N	0	216144983	2025-10-01 12:22:31	\N	\N	\N	\N
247	2025-09-12	682855	\N	0	216136684	2025-10-01 12:22:31	\N	\N	\N	\N
259	2025-09-12	682055	\N	0	215271873	2025-10-01 12:22:31	\N	\N	\N	\N
271	2025-09-12	682895	\N	0	216273158	2025-10-01 12:22:31	\N	\N	\N	\N
246	2025-09-12	682965	\N	0	216273167	2025-10-01 12:22:31	\N	\N	\N	\N
260	2025-09-12	682165	\N	0	215527197	2025-10-01 12:22:31	\N	\N	\N	\N
239	2025-09-12	680635	\N	0	214126153	2025-10-01 12:22:31	\N	\N	\N	\N
279	2025-09-12	682765	\N	0	216110444	2025-10-01 12:22:31	\N	\N	\N	\N
269	2025-09-12	100480	\N	0	216346884	2025-10-01 12:22:31	\N	\N	\N	\N
274	2025-09-12	682465	\N	0	215845072	2025-10-01 12:22:31	\N	\N	\N	\N
244	2025-09-12	682905	\N	0	216273159	2025-10-01 12:22:31	\N	\N	\N	\N
275	2025-09-12	100481	\N	0	216346742	2025-10-01 12:22:31	\N	\N	\N	\N
258	2025-09-12	100479	\N	0	216346700	2025-10-01 12:22:31	\N	\N	\N	\N
267	2025-09-12	682835	\N	0	216127466	2025-10-01 12:22:31	\N	\N	\N	\N
266	2025-09-12	100483	\N	0	216286636	2025-10-01 12:22:31	\N	\N	\N	\N
265	2025-09-12	682375	\N	0	215790341	2025-10-01 12:22:31	\N	\N	\N	\N
264	2025-09-12	682285	\N	0	215727987	2025-10-01 12:22:31	\N	\N	\N	\N
263	2025-09-12	682985	\N	0	216273168	2025-10-01 12:22:31	\N	\N	\N	\N
270	2025-09-12	682885	\N	0	216152312	2025-10-01 12:22:31	\N	\N	\N	\N
306	2025-09-15	100482	\N	0	216271417	2025-10-01 12:22:31	\N	\N	\N	\N
313	2025-09-15	683105	\N	0	216954524	2025-10-01 12:22:31	\N	\N	\N	\N
307	2025-09-15	683745	\N	0	216954721	2025-10-01 12:22:31	\N	\N	\N	\N
308	2025-09-15	683275	\N	0	216954604	2025-10-01 12:22:31	\N	\N	\N	\N
310	2025-09-15	683755	\N	0	216954722	2025-10-01 12:22:31	\N	\N	\N	\N
311	2025-09-15	683295	\N	0	216954608	2025-10-01 12:22:31	\N	\N	\N	\N
312	2025-09-15	683425	\N	0	216954649	2025-10-01 12:22:31	\N	\N	\N	\N
315	2025-09-15	683305	\N	0	216954609	2025-10-01 12:22:31	\N	\N	\N	\N
326	2025-09-15	683335	\N	0	216954617	2025-10-01 12:22:31	\N	\N	\N	\N
318	2025-09-15	683435	\N	0	216954651	2025-10-01 12:22:31	\N	\N	\N	\N
319	2025-09-15	683315	\N	0	216954612	2025-10-01 12:22:31	\N	\N	\N	\N
320	2025-09-15	683595	\N	0	216954693	2025-10-01 12:22:31	\N	\N	\N	\N
322	2025-09-15	683765	\N	0	216954724	2025-10-01 12:22:31	\N	\N	\N	\N
324	2025-09-15	683125	\N	0	216954541	2025-10-01 12:22:31	\N	\N	\N	\N
325	2025-09-15	683445	\N	0	216954655	2025-10-01 12:22:31	\N	\N	\N	\N
327	2025-09-15	683605	\N	0	216954695	2025-10-01 12:22:31	\N	\N	\N	\N
305	2025-09-15	683735	\N	0	216954720	2025-10-01 12:22:31	\N	\N	\N	\N
317	2025-09-15	683585	\N	0	216954690	2025-10-01 12:22:31	\N	\N	\N	\N
304	2025-09-15	683265	\N	0	216954601	2025-10-01 12:22:31	\N	\N	\N	\N
328	2025-09-15	683135	\N	0	216954544	2025-10-01 12:22:31	\N	\N	\N	\N
302	2025-09-15	683575	\N	0	216954689	2025-10-01 12:22:31	\N	\N	\N	\N
281	2025-09-15	683385	\N	0	216954636	2025-10-01 12:22:31	\N	\N	\N	\N
282	2025-09-15	683045	\N	0	216954490	2025-10-01 12:22:31	\N	\N	\N	\N
284	2025-09-15	683395	\N	0	216954639	2025-10-01 12:22:31	\N	\N	\N	\N
285	2025-09-15	683055	\N	0	216954492	2025-10-01 12:22:31	\N	\N	\N	\N
287	2025-09-15	683225	\N	0	216954580	2025-10-01 12:22:31	\N	\N	\N	\N
289	2025-09-15	683555	\N	0	216954685	2025-10-01 12:22:31	\N	\N	\N	\N
290	2025-09-15	683405	\N	0	216954643	2025-10-01 12:22:31	\N	\N	\N	\N
291	2025-09-15	682675	\N	0	216042905	2025-10-01 12:22:31	\N	\N	\N	\N
292	2025-09-15	683235	\N	0	216954583	2025-10-01 12:22:31	\N	\N	\N	\N
293	2025-09-15	683715	\N	0	216954718	2025-10-01 12:22:31	\N	\N	\N	\N
294	2025-09-15	683065	\N	0	216954497	2025-10-01 12:22:31	\N	\N	\N	\N
295	2025-09-15	683725	\N	0	216954719	2025-10-01 12:22:31	\N	\N	\N	\N
296	2025-09-15	683075	\N	0	216954508	2025-10-01 12:22:31	\N	\N	\N	\N
297	2025-09-15	683565	\N	0	216954687	2025-10-01 12:22:31	\N	\N	\N	\N
298	2025-09-15	683245	\N	0	216954586	2025-10-01 12:22:31	\N	\N	\N	\N
299	2025-09-15	683085	\N	0	216954513	2025-10-01 12:22:31	\N	\N	\N	\N
301	2025-09-15	683255	\N	0	216954597	2025-10-01 12:22:31	\N	\N	\N	\N
303	2025-09-15	683415	\N	0	216954646	2025-10-01 12:22:31	\N	\N	\N	\N
329	2025-09-15	683455	\N	0	216954658	2025-10-01 12:22:31	\N	\N	\N	\N
323	2025-09-15	683325	\N	0	216954615	2025-10-01 12:22:31	\N	\N	\N	\N
332	2025-09-15	683775	\N	0	216954725	2025-10-01 12:22:31	\N	\N	\N	\N
355	2025-09-15	683215	\N	0	216954576	2025-10-01 12:22:31	\N	\N	\N	\N
356	2025-09-15	683535	\N	0	216954677	2025-10-01 12:22:31	\N	\N	\N	\N
357	2025-09-15	683545	\N	0	216954682	2025-10-01 12:22:31	\N	\N	\N	\N
359	2025-09-15	683825	\N	0	216982585	2025-10-01 12:22:31	\N	\N	\N	\N
358	2025-09-15	683015	\N	0	216984415	2025-10-01 12:22:31	\N	\N	\N	\N
362	2025-09-15	683035	\N	0	216954484	2025-10-01 12:22:31	\N	\N	\N	\N
316	2025-09-15	683115	\N	0	216984779	2025-10-01 12:22:31	\N	\N	\N	\N
364	2025-09-15	683655	\N	0	216954708	2025-10-01 12:22:31	\N	\N	\N	\N
288	2025-09-15	683705	\N	0	216986527	2025-10-01 12:22:31	\N	\N	\N	\N
366	2025-09-15	683665	\N	0	216954710	2025-10-01 12:22:31	\N	\N	\N	\N
347	2025-09-15	683175	\N	0	216986819	2025-10-01 12:22:31	\N	\N	\N	\N
368	2025-09-15	683675	\N	0	216954712	2025-10-01 12:22:31	\N	\N	\N	\N
339	2025-09-15	683805	\N	0	216986914	2025-10-01 12:22:31	\N	\N	\N	\N
370	2025-09-15	683685	\N	0	216954713	2025-10-01 12:22:31	\N	\N	\N	\N
371	2025-09-15	683835	\N	0	216994772	2025-10-01 12:22:31	\N	\N	\N	\N
372	2025-09-15	683845	\N	0	217002705	2025-10-01 12:22:31	\N	\N	\N	\N
373	2025-09-15	683695	\N	0	216954714	2025-10-01 12:22:31	\N	\N	\N	\N
354	2025-09-15	683525	\N	0	216954675	2025-10-01 12:22:31	\N	\N	\N	\N
353	2025-09-15	683205	\N	0	216954574	2025-10-01 12:22:31	\N	\N	\N	\N
360	2025-09-15	683025	\N	0	216954483	2025-10-01 12:22:31	\N	\N	\N	\N
351	2025-09-15	683815	\N	0	216968331	2025-10-01 12:22:31	\N	\N	\N	\N
333	2025-09-15	683465	\N	0	216954660	2025-10-01 12:22:31	\N	\N	\N	\N
334	2025-09-15	683615	\N	0	216954697	2025-10-01 12:22:31	\N	\N	\N	\N
352	2025-09-15	683515	\N	0	216954671	2025-10-01 12:22:31	\N	\N	\N	\N
336	2025-09-15	683795	\N	0	216954726	2025-10-01 12:22:31	\N	\N	\N	\N
330	2025-09-15	683345	\N	0	216954621	2025-10-01 12:22:31	\N	\N	\N	\N
337	2025-09-15	683355	\N	0	216954628	2025-10-01 12:22:31	\N	\N	\N	\N
338	2025-09-15	683475	\N	0	216954666	2025-10-01 12:22:31	\N	\N	\N	\N
340	2025-09-15	683625	\N	0	216954699	2025-10-01 12:22:31	\N	\N	\N	\N
341	2025-09-15	683005	\N	0	216954479	2025-10-01 12:22:31	\N	\N	\N	\N
335	2025-09-15	682995	\N	0	216954477	2025-10-01 12:22:31	\N	\N	\N	\N
343	2025-09-15	683365	\N	0	216954630	2025-10-01 12:22:31	\N	\N	\N	\N
344	2025-09-15	683165	\N	0	216954553	2025-10-01 12:22:31	\N	\N	\N	\N
345	2025-09-15	683375	\N	0	216954632	2025-10-01 12:22:31	\N	\N	\N	\N
346	2025-09-15	683635	\N	0	216954703	2025-10-01 12:22:31	\N	\N	\N	\N
348	2025-09-15	683195	\N	0	216954565	2025-10-01 12:22:31	\N	\N	\N	\N
349	2025-09-15	683485	\N	0	216954668	2025-10-01 12:22:31	\N	\N	\N	\N
350	2025-09-15	683645	\N	0	216954706	2025-10-01 12:22:31	\N	\N	\N	\N
342	2025-09-15	683155	\N	0	216954548	2025-10-01 12:22:31	\N	\N	\N	\N
387	2025-09-16	683925	\N	0	217098193	2025-10-01 12:22:31	\N	\N	\N	\N
386	2025-09-16	684005	\N	0	217247591	2025-10-01 12:22:31	\N	\N	\N	\N
385	2025-09-16	683995	\N	0	217242617	2025-10-01 12:22:31	\N	\N	\N	\N
384	2025-09-16	683885	\N	0	217061087	2025-10-01 12:22:31	\N	\N	\N	\N
382	2025-09-16	683915	\N	0	217095645	2025-10-01 12:22:31	\N	\N	\N	\N
381	2025-09-16	683865	\N	0	217053461	2025-10-01 12:22:31	\N	\N	\N	\N
376	2025-09-16	684035	\N	0	217253610	2025-10-01 12:22:31	\N	\N	\N	\N
378	2025-09-16	684085	\N	0	217271844	2025-10-01 12:22:31	\N	\N	\N	\N
377	2025-09-16	683985	\N	0	217231599	2025-10-01 12:22:31	\N	\N	\N	\N
375	2025-09-16	683905	\N	0	217078383	2025-10-01 12:22:31	\N	\N	\N	\N
374	2025-09-16	683965	\N	0	217230171	2025-10-01 12:22:31	\N	\N	\N	\N
389	2025-09-16	684125	\N	0	217288907	2025-10-01 12:22:31	\N	\N	\N	\N
380	2025-09-16	684095	\N	0	217277273	2025-10-01 12:22:31	\N	\N	\N	\N
391	2025-09-16	684045	\N	0	217257079	2025-10-01 12:22:31	\N	\N	\N	\N
383	2025-09-16	683875	\N	0	217058376	2025-10-01 12:22:31	\N	\N	\N	\N
393	2025-09-16	684055	\N	0	217260957	2025-10-01 12:22:31	\N	\N	\N	\N
392	2025-09-16	684015	\N	0	217250600	2025-10-01 12:22:31	\N	\N	\N	\N
405	2025-09-16	684075	\N	0	217270719	2025-10-01 12:22:31	\N	\N	\N	\N
388	2025-09-16	100485	\N	0	217304180	2025-10-01 12:22:31	\N	\N	\N	\N
403	2025-09-16	684065	\N	0	217260960	2025-10-01 12:22:31	\N	\N	\N	\N
395	2025-09-16	683935	\N	0	217304077	2025-10-01 12:22:31	\N	\N	\N	\N
390	2025-09-16	683895	\N	0	217303960	2025-10-01 12:22:31	\N	\N	\N	\N
399	2025-09-16	684145	\N	0	217301712	2025-10-01 12:22:31	\N	\N	\N	\N
398	2025-09-16	100486	\N	0	217288207	2025-10-01 12:22:31	\N	\N	\N	\N
397	2025-09-16	683955	\N	0	217230170	2025-10-01 12:22:31	\N	\N	\N	\N
396	2025-09-16	684135	\N	0	217291618	2025-10-01 12:22:31	\N	\N	\N	\N
394	2025-09-16	684115	\N	0	217287238	2025-10-01 12:22:31	\N	\N	\N	\N
400	2025-09-16	684155	\N	0	217303177	2025-10-01 12:22:31	\N	\N	\N	\N
422	2025-09-17	684285	\N	0	217377798	2025-10-01 12:22:31	\N	\N	\N	\N
418	2025-09-17	684185	\N	0	217338336	2025-10-01 12:22:31	\N	\N	\N	\N
416	2025-09-17	684345	\N	0	217528363	2025-10-01 12:22:31	\N	\N	\N	\N
415	2025-09-17	684175	\N	0	217335811	2025-10-01 12:22:31	\N	\N	\N	\N
410	2025-09-17	684465	\N	0	217592768	2025-10-01 12:22:31	\N	\N	\N	\N
413	2025-09-17	684385	\N	0	217564628	2025-10-01 12:22:31	\N	\N	\N	\N
409	2025-09-17	684235	\N	0	217369691	2025-10-01 12:22:31	\N	\N	\N	\N
408	2025-09-17	684445	\N	0	217589896	2025-10-01 12:22:31	\N	\N	\N	\N
407	2025-09-17	684215	\N	0	217348441	2025-10-01 12:22:31	\N	\N	\N	\N
423	2025-09-17	684405	\N	0	217575620	2025-10-01 12:22:31	\N	\N	\N	\N
406	2025-09-17	684325	\N	0	217503540	2025-10-01 12:22:31	\N	\N	\N	\N
414	2025-09-17	684335	\N	0	217527319	2025-10-01 12:22:31	\N	\N	\N	\N
425	2025-09-17	684365	\N	0	217555814	2025-10-01 12:22:31	\N	\N	\N	\N
420	2025-09-17	684265	\N	0	217376728	2025-10-01 12:22:31	\N	\N	\N	\N
427	2025-09-17	684205	\N	0	217339515	2025-10-01 12:22:31	\N	\N	\N	\N
426	2025-09-17	100487	\N	0	217590005	2025-10-01 12:22:31	\N	\N	\N	\N
412	2025-09-17	684165	\N	0	217320525	2025-10-01 12:22:31	\N	\N	\N	\N
438	2025-09-17	684425	\N	0	217583306	2025-10-01 12:22:31	\N	\N	\N	\N
436	2025-09-17	684415	\N	0	217580827	2025-10-01 12:22:31	\N	\N	\N	\N
417	2025-09-17	684255	\N	0	217592268	2025-10-01 12:22:31	\N	\N	\N	\N
434	2025-09-17	100488	\N	0	217592114	2025-10-01 12:22:31	\N	\N	\N	\N
437	2025-09-17	100489	\N	0	217592563	2025-10-01 12:22:31	\N	\N	\N	\N
424	2025-09-17	684195	\N	0	217592321	2025-10-01 12:22:31	\N	\N	\N	\N
431	2025-09-17	684395	\N	0	217565869	2025-10-01 12:22:31	\N	\N	\N	\N
419	2025-09-17	684355	\N	0	217592372	2025-10-01 12:22:31	\N	\N	\N	\N
429	2025-09-17	684455	\N	0	217591457	2025-10-01 12:22:31	\N	\N	\N	\N
428	2025-09-17	100491	\N	0	217593748	2025-10-01 12:22:31	\N	\N	\N	\N
411	2025-09-17	684375	\N	0	217592202	2025-10-01 12:22:31	\N	\N	\N	\N
447	2025-09-18	684545	\N	0	217767623	2025-10-01 12:22:31	\N	\N	\N	\N
439	2025-09-18	684515	\N	0	217621797	2025-10-01 12:22:31	\N	\N	\N	\N
440	2025-09-18	684625	\N	0	217820000	2025-10-01 12:22:31	\N	\N	\N	\N
442	2025-09-18	684595	\N	0	217796170	2025-10-01 12:22:31	\N	\N	\N	\N
443	2025-09-18	684495	\N	0	217606402	2025-10-01 12:22:31	\N	\N	\N	\N
444	2025-09-18	684525	\N	0	217622780	2025-10-01 12:22:31	\N	\N	\N	\N
446	2025-09-18	100492	\N	0	217653315	2025-10-01 12:22:31	\N	\N	\N	\N
448	2025-09-18	684615	\N	0	217818653	2025-10-01 12:22:31	\N	\N	\N	\N
453	2025-09-18	684555	\N	0	217767625	2025-10-01 12:22:31	\N	\N	\N	\N
450	2025-09-18	684635	\N	0	217847289	2025-10-01 12:22:31	\N	\N	\N	\N
451	2025-09-18	684535	\N	0	217627254	2025-10-01 12:22:31	\N	\N	\N	\N
452	2025-09-18	684575	\N	0	217789901	2025-10-01 12:22:31	\N	\N	\N	\N
445	2025-09-18	684605	\N	0	217849441	2025-10-01 12:22:31	\N	\N	\N	\N
455	2025-09-18	684585	\N	0	217790533	2025-10-01 12:22:31	\N	\N	\N	\N
456	2025-09-18	684505	\N	0	217617657	2025-10-01 12:22:31	\N	\N	\N	\N
441	2025-09-18	684475	\N	0	217595244	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
449	2025-09-18	684565	\N	0	217767626	2025-10-01 12:22:31	\N	\N	\N	\N
463	2025-09-19	684675	\N	0	217873301	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
459	2025-09-19	684655	\N	0	217863961	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
460	2025-09-19	684685	\N	0	217874490	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
458	2025-09-19	684715	\N	0	217885172	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
462	2025-09-19	684665	\N	0	217866738	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
464	2025-09-19	684735	\N	0	218062885	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
470	2025-09-19	684775	\N	0	218133761	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
467	2025-09-19	684755	\N	0	218079422	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
461	2025-09-19	684695	\N	0	217879048	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
469	2025-09-19	684765	\N	0	218108932	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
471	2025-09-19	684785	\N	0	218133763	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
457	2025-09-19	684645	\N	0	217851121	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
466	2025-09-19	684725	\N	0	217907397	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
472	2025-09-22	684865	\N	0	218718940	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
473	2025-09-22	684885	\N	0	218732601	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
476	2025-09-22	684905	\N	0	218749022	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
479	2025-09-22	684955	\N	0	218790180	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
480	2025-09-22	684825	\N	0	218676704	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
481	2025-09-22	684875	\N	0	218725750	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
482	2025-09-22	684805	\N	0	218211025	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
478	2025-09-22	684915	\N	0	218749025	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
484	2025-09-22	684855	\N	0	218718937	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
485	2025-09-22	100493	\N	0	218730543	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
486	2025-09-22	684815	\N	0	218676702	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
475	2025-09-22	684925	\N	0	218768149	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
488	2025-09-22	684935	\N	0	218770311	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
477	2025-09-22	684945	\N	0	218770317	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
474	2025-09-22	684795	\N	0	218160234	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
483	2025-09-22	684835	\N	0	218676705	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
501	2025-09-23	685295	\N	0	219071397	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
505	2025-09-23	100494	\N	0	219003914	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
503	2025-09-23	685305	\N	0	219051054	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
502	2025-09-23	685065	\N	0	218851397	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
500	2025-09-23	685055	\N	0	218844881	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
499	2025-09-23	685125	\N	0	219002259	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
498	2025-09-23	685105	\N	0	218997197	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
493	2025-09-23	685145	\N	0	219008542	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
495	2025-09-23	685155	\N	0	219014222	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
494	2025-09-23	685035	\N	0	218838549	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
492	2025-09-23	685085	\N	0	218997195	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
491	2025-09-23	685285	\N	0	219051046	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
490	2025-09-23	685025	\N	0	218835497	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
507	2025-09-23	685075	\N	0	218866101	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
496	2025-09-23	685095	\N	0	218997196	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
508	2025-09-23	684965	\N	0	218792173	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
514	2025-09-23	685165	\N	0	219021674	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
510	2025-09-23	684975	\N	0	218804829	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
504	2025-09-23	685215	\N	0	219024116	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
525	2025-09-23	685205	\N	0	219024112	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
524	2025-09-23	685265	\N	0	219042936	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
523	2025-09-23	685135	\N	0	219004175	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
522	2025-09-23	685195	\N	0	219022614	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
521	2025-09-23	685015	\N	0	218827856	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
520	2025-09-23	685255	\N	0	219041820	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
526	2025-09-23	685275	\N	0	219045843	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
518	2025-09-23	685225	\N	0	219034335	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
517	2025-09-23	100495	\N	0	219033504	2025-10-01 12:22:31	fedex	556346	fedex_home_delivery	FedEx Home Delivery
516	2025-09-23	685185	\N	0	219022608	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
515	2025-09-23	684995	\N	0	218818058	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
512	2025-09-23	684985	\N	0	219071466	2025-10-01 12:22:31	fedex	556346	fedex_2day	FedEx 2Day
497	2025-09-23	685045	\N	0	219071423	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
519	2025-09-23	685005	\N	0	218820278	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
530	2025-09-24	685505	\N	0	219266176	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
529	2025-09-24	685315	\N	0	219085639	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
528	2025-09-24	685365	\N	0	219109288	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
527	2025-09-24	685415	\N	0	219132014	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
553	2025-09-24	685555	\N	0	219290983	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
548	2025-09-24	685545	\N	0	219288168	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
542	2025-09-24	685585	\N	0	219313028	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
544	2025-09-24	685605	\N	0	219330240	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
543	2025-09-24	685595	\N	0	219318229	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
541	2025-09-24	685525	\N	0	219280679	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
535	2025-09-24	685565	\N	0	219299941	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
537	2025-09-24	685515	\N	0	219272673	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
531	2025-09-24	685455	\N	0	219139214	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
539	2025-09-24	685575	\N	0	219336272	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
532	2025-09-24	685335	\N	0	219100789	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
557	2025-09-24	100498	\N	0	219137879	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
534	2025-09-24	685445	\N	0	219135417	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
533	2025-09-24	100496	\N	0	219135171	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
558	2025-09-24	685405	\N	0	219122407	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
556	2025-09-24	685395	\N	0	219122405	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
555	2025-09-24	685385	\N	0	219112992	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
552	2025-09-24	685375	\N	0	219109292	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
551	2025-09-24	685485	\N	0	219260754	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
554	2025-09-24	685495	\N	0	219260760	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
547	2025-09-24	685475	\N	0	219260751	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
546	2025-09-24	685355	\N	0	219105906	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
540	2025-09-24	685345	\N	0	219102281	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
538	2025-09-24	685465	\N	0	219145003	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
536	2025-09-24	100497	\N	0	219135531	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
550	2025-09-24	685325	\N	0	219107633	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
578	2025-09-25	685875	\N	0	219532526	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
575	2025-09-25	685765	\N	0	219531158	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
576	2025-09-25	685995	\N	0	219533184	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
577	2025-09-25	685865	\N	0	219532525	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
579	2025-09-25	686115	\N	0	219567509	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
585	2025-09-25	685785	\N	0	219531160	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
581	2025-09-25	685895	\N	0	219532530	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
582	2025-09-25	686195	\N	0	219591900	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
583	2025-09-25	685775	\N	0	219531159	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
584	2025-09-25	685905	\N	0	219532531	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
574	2025-09-25	685855	\N	0	219532524	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
580	2025-09-25	685885	\N	0	219532528	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
573	2025-09-25	685635	\N	0	219357958	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
566	2025-09-25	686105	\N	0	219555176	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
571	2025-09-25	100500	\N	0	219587646	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
570	2025-09-25	685625	\N	0	219354893	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
569	2025-09-25	685755	\N	0	219531157	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
568	2025-09-25	685975	\N	0	219533180	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
567	2025-09-25	686185	\N	0	219580672	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
563	2025-09-25	686095	\N	0	219555173	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
562	2025-09-25	685965	\N	0	219533179	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
561	2025-09-25	686085	\N	0	219536187	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
560	2025-09-25	685955	\N	0	219533177	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
559	2025-09-25	686175	\N	0	219579085	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
619	2025-09-25	100499	\N	0	219576123	2025-10-01 12:22:31	fedex	556346	fedex_ground_international	Fedex Ground International
620	2025-09-25	686245	\N	0	219621002	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
586	2025-09-25	686005	\N	0	219533186	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
572	2025-09-25	685985	\N	0	219533182	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
587	2025-09-25	685915	\N	0	219532532	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
600	2025-09-25	685655	\N	0	219369720	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
589	2025-09-25	685795	\N	0	219531161	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
565	2025-09-25	685615	\N	0	219346314	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
617	2025-09-25	685705	\N	0	219399224	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
616	2025-09-25	685685	\N	0	219382571	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
607	2025-09-25	685675	\N	0	219373794	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
614	2025-09-25	686055	\N	0	219534430	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
613	2025-09-25	686035	\N	0	219534428	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
612	2025-09-25	686025	\N	0	219534426	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
611	2025-09-25	686165	\N	0	219577423	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
610	2025-09-25	686155	\N	0	219577422	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
609	2025-09-25	686015	\N	0	219534424	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
608	2025-09-25	685665	\N	0	219370985	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
594	2025-09-25	685645	\N	0	219621314	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
605	2025-09-25	685945	\N	0	219533175	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
618	2025-09-25	685715	\N	0	219526400	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
564	2025-09-25	685745	\N	0	219621163	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
604	2025-09-25	686145	\N	0	219576386	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
590	2025-09-25	686215	\N	0	219598570	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
592	2025-09-25	685925	\N	0	219533172	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
593	2025-09-25	685815	\N	0	219531169	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
595	2025-09-25	686135	\N	0	219571019	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
591	2025-09-25	685805	\N	0	219531162	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
597	2025-09-25	686225	\N	0	219603137	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
598	2025-09-25	686235	\N	0	219607404	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
599	2025-09-25	685835	\N	0	219531946	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
588	2025-09-25	686125	\N	0	219568949	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
601	2025-09-25	685845	\N	0	219531947	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
596	2025-09-25	685935	\N	0	219533174	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
628	2025-09-26	686265	\N	0	219644375	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
622	2025-09-26	686315	\N	0	219661358	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
623	2025-09-26	686415	\N	0	219682811	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
624	2025-09-26	686255	\N	0	219642137	2025-10-01 12:22:31	fedex	556346	fedex_2day	FedEx 2Day
625	2025-09-26	686445	\N	0	219892964	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
626	2025-09-26	686325	\N	0	219665097	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
627	2025-09-26	686365	\N	0	219667733	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
629	2025-09-26	686385	\N	0	219677027	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
632	2025-09-26	686425	\N	0	219685427	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
631	2025-09-26	686455	\N	0	219892966	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
634	2025-09-26	686465	\N	0	219892967	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
635	2025-09-26	686485	\N	0	219892968	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
633	2025-09-26	100501	\N	0	219963558	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
638	2025-09-26	686505	\N	0	219978112	2025-10-01 12:22:31	\N	\N	\N	\N
630	2025-09-26	686275	\N	0	219647952	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
642	2025-09-29	686665	\N	0	220589405	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
641	2025-09-29	686685	\N	0	220595662	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
644	2025-09-29	686675	\N	0	220594167	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
653	2025-09-29	686695	\N	0	220597061	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
654	2025-09-29	100503	\N	0	220600499	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
655	2025-09-29	686705	\N	0	220615990	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
639	2025-09-29	686655	\N	0	220589402	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
640	2025-09-29	686515	\N	0	219982943	2025-10-01 12:22:31	\N	\N	\N	\N
643	2025-09-29	686545	\N	0	220517780	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
649	2025-09-29	686555	\N	0	220517782	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
646	2025-09-29	686525	\N	0	220013013	2025-10-01 12:22:31	\N	\N	\N	\N
647	2025-09-29	686595	\N	0	220541848	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
648	2025-09-29	686605	\N	0	220545596	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
650	2025-09-29	686535	\N	0	220023095	2025-10-01 12:22:31	\N	\N	\N	\N
651	2025-09-29	686575	\N	0	220525848	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
652	2025-09-29	686635	\N	0	220562441	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
656	2025-09-29	100502	\N	0	220563105	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
657	2025-09-29	686645	\N	0	220579521	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
645	2025-09-29	686585	\N	0	220538591	2025-10-01 12:22:31	fedex	556346	fedex_ground	FedEx Ground
1427	2025-09-30	686805	\N	0	220836881	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1413	2025-09-30	686815	\N	0	220836882	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1414	2025-09-30	686765	\N	0	220671185	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1415	2025-09-30	686825	\N	0	220848780	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1416	2025-09-30	686745	\N	0	220652163	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1417	2025-09-30	686795	\N	0	220836880	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1418	2025-09-30	686735	\N	0	220648018	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1425	2025-09-30	686785	\N	0	220836879	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1420	2025-09-30	686755	\N	0	220662704	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1421	2025-09-30	686845	\N	0	220852454	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1422	2025-09-30	686875	\N	0	220863693	2025-10-01 13:49:27	fedex	556346	fedex_home_delivery	FedEx Home Delivery
1419	2025-09-30	686895	\N	0	220878880	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1423	2025-09-30	686905	\N	0	220910954	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1424	2025-09-30	686715	\N	0	220629517	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
1426	2025-09-30	686775	\N	0	220690241	2025-10-01 13:49:27	fedex	556346	fedex_ground	FedEx Ground
2199	2025-10-01	687305	\N	0	221169385	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2200	2025-10-01	687385	\N	0	221224180	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2201	2025-10-01	687295	\N	0	221167940	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2202	2025-10-01	687375	\N	0	221217343	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2203	2025-10-01	687285	\N	0	221156452	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2204	2025-10-01	687365	\N	0	221214652	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2205	2025-10-01	687275	\N	0	221139204	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2216	2025-10-01	687265	\N	0	221139202	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2208	2025-10-01	687245	\N	0	221139201	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2211	2025-10-01	687325	\N	0	221191661	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2209	2025-10-01	687345	\N	0	221200002	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2210	2025-10-01	687335	\N	0	221197163	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2212	2025-10-01	687315	\N	0	221184792	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2213	2025-10-01	687415	\N	0	221238887	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2214	2025-10-01	687405	\N	0	221236487	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2206	2025-10-01	687395	\N	0	221231699	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2220	2025-10-01	687205	\N	0	221139200	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2240	2025-10-01	687195	\N	0	221139199	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2198	2025-10-01	687085	\N	0	220995322	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2207	2025-10-01	687355	\N	0	221206638	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2215	2025-10-01	686915	\N	0	220944277	2025-10-01 19:32:37	fedex	556346	fedex_2day	FedEx 2Day
2238	2025-10-01	686955	\N	0	220954357	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2239	2025-10-01	686945	\N	0	220952822	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2221	2025-10-01	686725	\N	0	220646610	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2222	2025-10-01	687185	\N	0	221139198	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2223	2025-10-01	687175	\N	0	221139197	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2224	2025-10-01	687155	\N	0	221139196	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2226	2025-10-01	687075	\N	0	220990967	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2227	2025-10-01	687055	\N	0	220972810	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2228	2025-10-01	687045	\N	0	220971691	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2229	2025-10-01	687125	\N	0	221001966	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2218	2025-10-01	687035	\N	0	220971690	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2225	2025-10-01	687145	\N	0	221139195	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2231	2025-10-01	686985	\N	0	220964829	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2232	2025-10-01	687015	\N	0	220967483	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2233	2025-10-01	686965	\N	0	220961430	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2234	2025-10-01	687005	\N	0	220967480	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2235	2025-10-01	686975	\N	0	220959961	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2236	2025-10-01	687105	\N	0	221001963	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2237	2025-10-01	687095	\N	0	221000390	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2217	2025-10-01	686925	\N	0	220948352	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2219	2025-10-01	686995	\N	0	220964830	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
2230	2025-10-01	687025	\N	0	220968908	2025-10-01 19:32:37	fedex	556346	fedex_ground	FedEx Ground
3836	2025-10-02	687615	\N	0	221424893	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3837	2025-10-02	687485	\N	0	221273193	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3838	2025-10-02	687725	\N	0	221492173	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3844	2025-10-02	687455	\N	0	221250832	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3840	2025-10-02	687635	\N	0	221423484	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3858	2025-10-02	687715	\N	0	221476932	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3839	2025-10-02	687435	\N	0	221245775	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3842	2025-10-02	687595	\N	0	221306668	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3856	2025-10-02	687425	\N	0	221240989	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3835	2025-10-02	687675	\N	0	221466075	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3841	2025-10-02	100504	\N	0	221309303	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3843	2025-10-02	687605	\N	0	221424967	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3852	2025-10-02	687665	\N	0	221462730	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3857	2025-10-02	687645	\N	0	221453324	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3855	2025-10-02	687585	\N	0	221300929	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3846	2025-10-02	687705	\N	0	221472083	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3845	2025-10-02	687625	\N	0	221423633	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3853	2025-10-02	687775	\N	0	221519274	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3854	2025-10-02	687555	\N	0	221284689	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3850	2025-10-02	687465	\N	0	221253770	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3849	2025-10-02	687735	\N	0	221495177	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3848	2025-10-02	687695	\N	0	221471140	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3847	2025-10-02	687685	\N	0	221469791	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
3851	2025-10-02	687545	\N	0	221283358	2025-10-02 17:18:52	fedex	556346	fedex_ground	FedEx Ground
4709	2025-10-03	687885	\N	0	221797210	2025-10-03 17:02:36	fedex	556346	fedex_ground	FedEx Ground
4682	2025-10-03	687795	\N	0	221549747	2025-10-02 20:53:06	fedex	556346	fedex_ground	FedEx Ground
4691	2025-10-03	687865	\N	0	221755391	2025-10-03 13:50:57	fedex	556346	fedex_ground	FedEx Ground
4693	2025-10-03	687845	\N	0	221613718	2025-10-03 13:50:58	fedex	556346	fedex_ground	FedEx Ground
4683	2025-10-03	687785	\N	0	221530150	2025-10-02 20:53:06	fedex	556346	fedex_ground	FedEx Ground
4688	2025-10-03	687835	\N	0	221588581	2025-10-02 21:05:10	fedex	556346	fedex_ground	FedEx Ground
4690	2025-10-03	100505	\N	0	221567336	2025-10-02 23:39:51	fedex	556346	fedex_ground	FedEx Ground
4680	2025-10-03	687815	\N	0	221576000	2025-10-02 20:53:05	fedex	556346	fedex_ground	FedEx Ground
4689	2025-10-03	687825	\N	0	221588580	2025-10-02 21:05:10	fedex	556346	fedex_ground	FedEx Ground
4710	2025-10-03	686065	\N	0	219534433	2025-10-03 17:14:14	fedex	556346	fedex_ground	FedEx Ground
4681	2025-10-03	687805	\N	0	221552729	2025-10-02 20:53:06	fedex	556346	fedex_ground	FedEx Ground
12330	2025-10-07	688595	\N	0	222563678	2025-10-06 20:45:13	fedex	556346	fedex_ground	FedEx Ground
13055	2025-10-07	688065	\N	0	222402610	2025-10-10 20:16:10	\N	\N	\N	\N
13056	2025-10-07	688395	\N	0	222405894	2025-10-10 20:16:10	\N	\N	\N	\N
13057	2025-10-07	688075	\N	0	222402613	2025-10-10 20:16:10	\N	\N	\N	\N
13058	2025-10-07	687975	\N	0	222400698	2025-10-10 20:16:10	\N	\N	\N	\N
13059	2025-10-07	687985	\N	0	222400705	2025-10-10 20:16:10	\N	\N	\N	\N
13060	2025-10-07	688085	\N	0	222402617	2025-10-10 20:16:10	\N	\N	\N	\N
13061	2025-10-07	688215	\N	0	222404845	2025-10-10 20:16:10	\N	\N	\N	\N
13062	2025-10-07	688405	\N	0	222406901	2025-10-10 20:16:10	\N	\N	\N	\N
13063	2025-10-07	688335	\N	0	222405860	2025-10-10 20:16:10	\N	\N	\N	\N
13064	2025-10-07	688225	\N	0	222404853	2025-10-10 20:16:10	\N	\N	\N	\N
13065	2025-10-07	688235	\N	0	222404858	2025-10-10 20:16:10	\N	\N	\N	\N
13066	2025-10-07	688415	\N	0	222406908	2025-10-10 20:16:10	\N	\N	\N	\N
13088	2025-10-07	688325	\N	0	222405855	2025-10-10 20:16:10	\N	\N	\N	\N
13068	2025-10-07	688205	\N	0	222403641	2025-10-10 20:16:10	\N	\N	\N	\N
13069	2025-10-07	688305	\N	0	222405846	2025-10-10 20:16:10	\N	\N	\N	\N
12331	2025-10-07	688585	\N	0	222563666	2025-10-06 20:45:13	fedex	556346	fedex_ground	FedEx Ground
13071	2025-10-07	688345	\N	0	222405869	2025-10-10 20:16:10	\N	\N	\N	\N
13072	2025-10-07	688685	\N	0	222744121	2025-10-10 20:16:10	\N	\N	\N	\N
13073	2025-10-07	688715	\N	0	222758611	2025-10-10 20:16:10	\N	\N	\N	\N
13074	2025-10-07	688725	\N	0	222761946	2025-10-10 20:16:10	\N	\N	\N	\N
13075	2025-10-07	688695	\N	0	222748075	2025-10-10 20:16:10	\N	\N	\N	\N
13076	2025-10-07	688665	\N	0	222705809	2025-10-10 20:16:10	\N	\N	\N	\N
13077	2025-10-07	688735	\N	0	222766365	2025-10-10 20:16:10	\N	\N	\N	\N
13078	2025-10-07	688705	\N	0	222782542	2025-10-10 20:16:10	\N	\N	\N	\N
13079	2025-10-07	688655	\N	0	222705190	2025-10-10 20:16:10	\N	\N	\N	\N
10706	2025-10-07	688535	\N	0	222542118	2025-10-06 19:45:12	fedex	556346	fedex_ground	FedEx Ground
13081	2025-10-07	687945	\N	0	222399365	2025-10-10 20:16:10	\N	\N	\N	\N
10705	2025-10-07	688545	\N	0	222543960	2025-10-06 19:45:12	fedex	556346	fedex_ground	FedEx Ground
12346	2025-10-07	100507	\N	0	222760861	2025-10-07 21:32:36	\N	\N	\N	\N
12332	2025-10-07	688555	\N	0	222559478	2025-10-06 20:45:13	fedex	556346	fedex_ground	FedEx Ground
13085	2025-10-07	687955	\N	0	222400685	2025-10-10 20:16:10	\N	\N	\N	\N
13086	2025-10-07	688195	\N	0	222403635	2025-10-10 20:16:10	\N	\N	\N	\N
13087	2025-10-07	688245	\N	0	222404860	2025-10-10 20:16:10	\N	\N	\N	\N
13083	2025-10-07	688055	\N	0	222402604	2025-10-10 20:16:10	\N	\N	\N	\N
13089	2025-10-07	688255	\N	0	222404876	2025-10-10 20:16:10	\N	\N	\N	\N
13090	2025-10-07	688445	\N	0	222406927	2025-10-10 20:16:10	\N	\N	\N	\N
13091	2025-10-07	688285	\N	0	222404896	2025-10-10 20:16:10	\N	\N	\N	\N
13092	2025-10-07	688295	\N	0	222404914	2025-10-10 20:16:10	\N	\N	\N	\N
12345	2025-10-07	100506	\N	0	222454310	2025-10-07 08:43:12	\N	\N	\N	\N
13094	2025-10-07	688455	\N	0	222406930	2025-10-10 20:16:10	\N	\N	\N	\N
13095	2025-10-07	688175	\N	0	222403625	2025-10-10 20:16:10	\N	\N	\N	\N
13096	2025-10-07	688185	\N	0	222403631	2025-10-10 20:16:10	\N	\N	\N	\N
13097	2025-10-07	688465	\N	0	222406935	2025-10-10 20:16:10	\N	\N	\N	\N
13098	2025-10-07	688485	\N	0	222459244	2025-10-10 20:16:10	\N	\N	\N	\N
13099	2025-10-07	688495	\N	0	222471649	2025-10-10 20:16:10	\N	\N	\N	\N
13100	2025-10-07	688525	\N	0	222612813	2025-10-10 20:16:10	\N	\N	\N	\N
13101	2025-10-07	688475	\N	0	222679060	2025-10-10 20:16:10	\N	\N	\N	\N
13102	2025-10-07	688645	\N	0	222689040	2025-10-10 20:16:10	\N	\N	\N	\N
13103	2025-10-07	687935	\N	0	221951872	2025-10-10 20:16:10	\N	\N	\N	\N
13104	2025-10-07	688095	\N	0	222402621	2025-10-10 20:16:10	\N	\N	\N	\N
12343	2025-10-07	688635	\N	0	222586384	2025-10-06 22:45:17	fedex	556346	fedex_ground	FedEx Ground
13106	2025-10-07	688275	\N	0	222404886	2025-10-10 20:16:10	\N	\N	\N	\N
7459	2025-10-07	688505	\N	0	222489596	2025-10-06 17:45:11	fedex	556346	fedex_ground	FedEx Ground
13108	2025-10-07	688385	\N	0	222405886	2025-10-10 20:16:10	\N	\N	\N	\N
13109	2025-10-07	688105	\N	0	222402625	2025-10-10 20:16:10	\N	\N	\N	\N
13110	2025-10-07	688355	\N	0	222405872	2025-10-10 20:16:10	\N	\N	\N	\N
13111	2025-10-07	688435	\N	0	222406921	2025-10-10 20:16:10	\N	\N	\N	\N
13112	2025-10-07	688145	\N	0	222403609	2025-10-10 20:16:10	\N	\N	\N	\N
13113	2025-10-07	688005	\N	0	222400725	2025-10-10 20:16:10	\N	\N	\N	\N
12334	2025-10-07	688605	\N	0	222573284	2025-10-06 21:45:14	fedex	556346	fedex_ground	FedEx Ground
13115	2025-10-07	688425	\N	0	222406914	2025-10-10 20:16:10	\N	\N	\N	\N
13116	2025-10-07	688015	\N	0	222400731	2025-10-10 20:16:10	\N	\N	\N	\N
13117	2025-10-07	687995	\N	0	222400713	2025-10-10 20:16:10	\N	\N	\N	\N
13118	2025-10-07	688025	\N	0	222402595	2025-10-10 20:16:10	\N	\N	\N	\N
13119	2025-10-07	688365	\N	0	222405876	2025-10-10 20:16:10	\N	\N	\N	\N
13120	2025-10-07	688035	\N	0	222402600	2025-10-10 20:16:10	\N	\N	\N	\N
13121	2025-10-07	688155	\N	0	222403614	2025-10-10 20:16:10	\N	\N	\N	\N
13122	2025-10-07	688375	\N	0	222405882	2025-10-10 20:16:10	\N	\N	\N	\N
13123	2025-10-07	688165	\N	0	222403621	2025-10-10 20:16:10	\N	\N	\N	\N
12333	2025-10-07	688625	\N	0	222584759	2025-10-06 21:45:14	fedex	556346	fedex_ground	FedEx Ground
13125	2025-10-07	688265	\N	0	222404880	2025-10-10 20:16:10	\N	\N	\N	\N
13126	2025-10-08	688925	\N	0	223006443	2025-10-10 20:16:10	\N	\N	\N	\N
13127	2025-10-08	688825	\N	0	222828059	2025-10-10 20:16:10	\N	\N	\N	\N
13128	2025-10-08	688875	\N	0	222850238	2025-10-10 20:16:10	\N	\N	\N	\N
13129	2025-10-08	689045	\N	0	223044564	2025-10-10 20:16:10	\N	\N	\N	\N
13130	2025-10-08	688815	\N	0	222821615	2025-10-10 20:16:10	\N	\N	\N	\N
13133	2025-10-08	688905	\N	0	222988025	2025-10-10 20:16:10	\N	\N	\N	\N
13131	2025-10-08	688805	\N	0	222821614	2025-10-10 20:16:10	\N	\N	\N	\N
13136	2025-10-08	688855	\N	0	222840204	2025-10-10 20:16:10	\N	\N	\N	\N
13137	2025-10-08	689055	\N	0	223049395	2025-10-10 20:16:10	\N	\N	\N	\N
13138	2025-10-08	688985	\N	0	223032621	2025-10-10 20:16:10	\N	\N	\N	\N
13139	2025-10-08	688885	\N	0	222859716	2025-10-10 20:16:10	\N	\N	\N	\N
13132	2025-10-08	689035	\N	0	223040692	2025-10-10 20:16:10	\N	\N	\N	\N
13141	2025-10-08	688945	\N	0	223013701	2025-10-10 20:16:10	\N	\N	\N	\N
13143	2025-10-08	688795	\N	0	222809458	2025-10-10 20:16:10	\N	\N	\N	\N
13144	2025-10-08	688785	\N	0	222809455	2025-10-10 20:16:10	\N	\N	\N	\N
13148	2025-10-08	688765	\N	0	222803848	2025-10-10 20:16:10	\N	\N	\N	\N
13145	2025-10-08	688755	\N	0	222794471	2025-10-10 20:16:10	\N	\N	\N	\N
13142	2025-10-08	688895	\N	0	222870004	2025-10-10 20:16:10	\N	\N	\N	\N
12347	2025-10-08	100508	\N	0	223022623	2025-10-09 20:49:12	\N	\N	\N	\N
13146	2025-10-08	688745	\N	0	222788648	2025-10-10 20:16:10	\N	\N	\N	\N
13149	2025-10-08	689015	\N	0	223038631	2025-10-10 20:16:10	\N	\N	\N	\N
13150	2025-10-08	688965	\N	0	223021465	2025-10-10 20:16:10	\N	\N	\N	\N
13151	2025-10-08	688835	\N	0	223069905	2025-10-10 20:16:10	\N	\N	\N	\N
13152	2025-10-08	688845	\N	0	222838734	2025-10-10 20:16:10	\N	\N	\N	\N
13153	2025-10-08	689065	\N	0	223057524	2025-10-10 20:16:10	\N	\N	\N	\N
13154	2025-10-08	688955	\N	0	223014738	2025-10-10 20:16:10	\N	\N	\N	\N
13155	2025-10-08	689025	\N	0	223040689	2025-10-10 20:16:10	\N	\N	\N	\N
13163	2025-10-09	689225	\N	0	223274020	2025-10-10 20:16:10	\N	\N	\N	\N
13159	2025-10-09	689175	\N	0	223134287	2025-10-10 20:16:10	\N	\N	\N	\N
13160	2025-10-09	689145	\N	0	223105001	2025-10-10 20:16:10	\N	\N	\N	\N
13161	2025-10-09	689095	\N	0	223090890	2025-10-10 20:16:10	\N	\N	\N	\N
13162	2025-10-09	689165	\N	0	223134282	2025-10-10 20:16:10	\N	\N	\N	\N
12353	2025-10-09	100514	\N	0	223313392	2025-10-09 20:49:12	\N	\N	\N	\N
13172	2025-10-09	689085	\N	0	223086547	2025-10-10 20:16:10	\N	\N	\N	\N
12358	2025-10-09	100522	\N	0	223387885	2025-10-09 20:49:12	\N	\N	\N	\N
13166	2025-10-09	689205	\N	0	223258235	2025-10-10 20:16:10	\N	\N	\N	\N
12354	2025-10-09	100518	\N	0	223387725	2025-10-09 20:49:12	\N	\N	\N	\N
12357	2025-10-09	100521	\N	0	223387873	2025-10-09 20:49:12	\N	\N	\N	\N
12359	2025-10-09	100523	\N	0	223387942	2025-10-09 20:49:12	\N	\N	\N	\N
12356	2025-10-09	100520	\N	0	223387853	2025-10-09 20:49:12	\N	\N	\N	\N
13157	2025-10-09	689155	\N	0	223108608	2025-10-10 20:16:10	\N	\N	\N	\N
12355	2025-10-09	100519	\N	0	223387752	2025-10-09 20:49:12	\N	\N	\N	\N
13165	2025-10-09	689315	\N	0	223298511	2025-10-10 20:16:10	\N	\N	\N	\N
13173	2025-10-09	689105	\N	0	223092345	2025-10-10 20:16:10	\N	\N	\N	\N
12350	2025-10-09	100511	\N	0	223135150	2025-10-09 20:49:12	\N	\N	\N	\N
13174	2025-10-09	689185	\N	0	223149407	2025-10-10 20:16:10	\N	\N	\N	\N
12352	2025-10-09	100513	\N	0	223286829	2025-10-09 20:49:12	\N	\N	\N	\N
13176	2025-10-09	689285	\N	0	223295533	2025-10-10 20:16:10	\N	\N	\N	\N
13183	2025-10-09	689275	\N	0	223294533	2025-10-10 20:16:10	\N	\N	\N	\N
13178	2025-10-09	689115	\N	0	223353330	2025-10-10 20:16:10	\N	\N	\N	\N
13180	2025-10-09	689135	\N	0	223352903	2025-10-10 20:16:10	\N	\N	\N	\N
13182	2025-10-09	689345	\N	0	223343932	2025-10-10 20:16:10	\N	\N	\N	\N
12349	2025-10-09	100510	\N	0	223133439	2025-10-09 20:49:12	\N	\N	\N	\N
13181	2025-10-09	689255	\N	0	223290272	2025-10-10 20:16:10	\N	\N	\N	\N
13185	2025-10-09	689335	\N	0	223324558	2025-10-10 20:16:10	\N	\N	\N	\N
13186	2025-10-09	689125	\N	0	223101636	2025-10-10 20:16:10	\N	\N	\N	\N
13187	2025-10-09	689245	\N	0	223276005	2025-10-10 20:16:10	\N	\N	\N	\N
13188	2025-10-09	689325	\N	0	223323308	2025-10-10 20:16:10	\N	\N	\N	\N
13189	2025-10-09	689195	\N	0	223165607	2025-10-10 20:16:10	\N	\N	\N	\N
13190	2025-10-09	689235	\N	0	223274958	2025-10-10 20:16:10	\N	\N	\N	\N
12348	2025-10-09	100509	\N	0	223115617	2025-10-09 20:49:12	\N	\N	\N	\N
12351	2025-10-09	100512	\N	0	223286454	2025-10-09 20:49:12	\N	\N	\N	\N
13204	2025-10-10	689465	\N	0	223704305	2025-10-10 20:16:10	\N	\N	\N	\N
13202	2025-10-10	689415	\N	0	223429548	2025-10-10 20:16:10	\N	\N	\N	\N
13192	2025-10-10	689435	\N	0	223766669	2025-10-10 20:16:10	\N	\N	\N	\N
13193	2025-10-10	689425	\N	0	223432822	2025-10-10 20:16:10	\N	\N	\N	\N
14853	2025-10-13	689485	\N	0	224351377	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14851	2025-10-13	689645	\N	0	224432333	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14855	2025-10-13	689655	\N	0	224433593	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14050	2025-10-13	100526	\N	0	224435389	2025-10-13 19:52:04	\N	\N	\N	\N
14857	2025-10-13	689665	\N	0	224437383	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14858	2025-10-13	689495	\N	0	224351382	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14859	2025-10-13	689615	\N	0	224402898	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14860	2025-10-14	689915	\N	0	224723211	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14861	2025-10-14	689795	\N	0	224520182	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14862	2025-10-14	689785	\N	0	224504368	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14863	2025-10-14	689945	\N	0	224738760	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14864	2025-10-14	689885	\N	0	224692567	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14865	2025-10-14	689855	\N	0	224607913	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14866	2025-10-14	689865	\N	0	224610323	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14867	2025-10-14	689905	\N	0	224708330	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14868	2025-10-14	689695	\N	0	224458669	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14869	2025-10-14	689675	\N	0	224447301	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14870	2025-10-14	689685	\N	0	224450354	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14871	2025-10-14	689715	\N	0	224471034	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14872	2025-10-14	689745	\N	0	224486172	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14873	2025-10-14	689755	\N	0	224502244	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14874	2025-10-14	689825	\N	0	224551458	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14875	2025-10-14	689895	\N	0	224704339	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14876	2025-10-14	689815	\N	0	224780636	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14877	2025-10-14	689975	\N	0	224764398	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14878	2025-10-14	689965	\N	0	224760479	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14879	2025-10-14	689985	\N	0	224775606	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14880	2025-10-14	689935	\N	0	224736413	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14881	2025-10-14	689775	\N	0	224504367	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14882	2025-10-14	689925	\N	0	224734472	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14883	2025-10-14	689765	\N	0	224502248	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14884	2025-10-14	689955	\N	0	224760476	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14901	2025-10-15	690685	\N	0	225006644	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14891	2025-10-15	690695	\N	0	225006651	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14885	2025-10-15	690325	\N	0	225001919	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14944	2025-10-15	690355	\N	0	225001930	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14906	2025-10-15	690785	\N	0	225028494	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14907	2025-10-15	690645	\N	0	225006633	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14908	2025-10-15	690795	\N	0	225039985	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14890	2025-10-15	690445	\N	0	225004501	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14904	2025-10-15	690805	\N	0	225041568	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14911	2025-10-15	690365	\N	0	225001932	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14912	2025-10-15	690505	\N	0	225004515	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14905	2025-10-15	690855	\N	0	225057103	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14913	2025-10-15	690815	\N	0	225047274	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14924	2025-10-15	690655	\N	0	225006636	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14916	2025-10-15	690375	\N	0	225001934	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
13195	2025-10-10	100517	\N	0	223364508	2025-10-10 20:16:10	\N	\N	\N	\N
13200	2025-10-10	100516	\N	0	223363554	2025-10-10 20:16:10	\N	\N	\N	\N
13203	2025-10-10	689385	\N	0	223415095	2025-10-10 20:16:10	\N	\N	\N	\N
13198	2025-10-10	689455	\N	0	223692299	2025-10-10 20:16:10	\N	\N	\N	\N
13199	2025-10-10	100515	\N	0	223362625	2025-10-10 20:16:10	\N	\N	\N	\N
13197	2025-10-10	689395	\N	0	223417928	2025-10-10 20:16:10	\N	\N	\N	\N
13201	2025-10-10	689405	\N	0	223429545	2025-10-10 20:16:10	\N	\N	\N	\N
13196	2025-10-10	100525	\N	0	223770778	2025-10-10 20:16:10	\N	\N	\N	\N
14843	2025-10-13	689605	\N	0	224393804	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14844	2025-10-13	689595	\N	0	224379969	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14845	2025-10-13	689505	\N	0	224358136	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14846	2025-10-13	689575	\N	0	224365077	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14847	2025-10-13	689625	\N	0	224405464	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14849	2025-10-13	689585	\N	0	224366297	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14848	2025-10-13	689475	\N	0	224357897	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14850	2025-10-13	689515	\N	0	224351389	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14854	2025-10-13	689635	\N	0	224405468	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14852	2025-10-13	689565	\N	0	224351402	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14917	2025-10-15	690515	\N	0	225004518	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14918	2025-10-15	690385	\N	0	225003323	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14919	2025-10-15	690525	\N	0	225005520	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14920	2025-10-15	690305	\N	0	225001912	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14921	2025-10-15	690665	\N	0	225006638	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14922	2025-10-15	690845	\N	0	225050208	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14915	2025-10-15	690835	\N	0	225048486	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14910	2025-10-15	690745	\N	0	225007530	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14926	2025-10-15	100530	\N	0	225073060	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14957	2025-10-15	690765	\N	0	225009840	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14945	2025-10-15	690265	\N	0	224999439	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14928	2025-10-15	690275	\N	0	224999441	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14929	2025-10-15	690285	\N	0	225001908	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14930	2025-10-15	690295	\N	0	225001910	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14931	2025-10-15	690045	\N	0	224817697	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14932	2025-10-15	690055	\N	0	224829192	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14933	2025-10-15	690075	\N	0	224840917	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14934	2025-10-15	690085	\N	0	224844497	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14946	2025-10-15	690255	\N	0	224999435	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14935	2025-10-15	690115	\N	0	224851111	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14937	2025-10-15	690145	\N	0	224867972	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14938	2025-10-15	690155	\N	0	224872603	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14939	2025-10-15	690165	\N	0	224979931	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14940	2025-10-15	690175	\N	0	224998139	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14941	2025-10-15	690185	\N	0	224998148	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14942	2025-10-15	690195	\N	0	224999416	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14943	2025-10-15	690205	\N	0	224999418	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14968	2025-10-15	690635	\N	0	225006630	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14936	2025-10-15	690135	\N	0	224861457	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14925	2025-10-15	690455	\N	0	225004504	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14947	2025-10-15	690245	\N	0	224999433	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14966	2025-10-15	690225	\N	0	224999428	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14927	2025-10-15	690465	\N	0	225004506	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14949	2025-10-15	690575	\N	0	225005536	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14950	2025-10-15	690865	\N	0	225070393	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14951	2025-10-15	690475	\N	0	225004508	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14952	2025-10-15	690775	\N	0	225016396	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14953	2025-10-15	690585	\N	0	225005538	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14954	2025-10-15	690595	\N	0	225005540	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14955	2025-10-15	690485	\N	0	225004509	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14948	2025-10-15	690235	\N	0	224999430	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14956	2025-10-15	690605	\N	0	225005542	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14967	2025-10-15	100527	\N	0	225073031	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
14959	2025-10-15	690625	\N	0	225006627	2025-10-15 19:53:53.388445+00	\N	\N	\N	\N
\.


--
-- Data for Name: shipping_violations; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.shipping_violations (id, order_id, order_number, violation_type, expected_value, actual_value, detected_at, resolved_at, is_resolved) FROM stdin;
1	35	686915	hawaiian_service	FedEx 2Day	FedEx Ground	2025-10-03 16:34:45	2025-10-03 16:36:36	1
5	268	100499	canadian_service	FedEx International Ground	Fedex Ground International	2025-10-03 19:01:22	2025-10-03 19:26:49	1
6	110	682585	canadian_service	FedEx International Ground	Fedex International Priority Express	2025-10-03 19:01:22	2025-10-03 19:26:53	1
\.


--
-- Data for Name: shipstation_metrics; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.shipstation_metrics (id, metric_name, metric_value, last_updated) FROM stdin;
1	units_to_ship	2	2025-10-16 17:29:10.790141+00
\.


--
-- Data for Name: shipstation_order_line_items; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.shipstation_order_line_items (id, order_inbox_id, sku, shipstation_order_id, created_at) FROM stdin;
1	546	17612	224998148	2025-10-15 16:56:52.650936+00
2	547	17612	224999416	2025-10-15 16:56:52.650936+00
3	548	17612	224999418	2025-10-15 16:56:52.650936+00
4	549	17612	224999421	2025-10-15 16:56:52.650936+00
5	550	17612	224999428	2025-10-15 16:56:52.650936+00
6	551	17612	224999430	2025-10-15 16:56:52.650936+00
7	552	17612	224999433	2025-10-15 16:56:52.650936+00
8	553	17612	224999435	2025-10-15 16:56:52.650936+00
9	554	17612	224999439	2025-10-15 16:56:52.650936+00
10	555	17612	224999441	2025-10-15 16:56:52.650936+00
11	556	17612	225001908	2025-10-15 16:56:52.650936+00
12	557	17612	225001910	2025-10-15 16:56:52.650936+00
13	558	17612	225001912	2025-10-15 16:56:52.650936+00
14	559	17612	225001916	2025-10-15 16:56:52.650936+00
15	560	17612	225001919	2025-10-15 16:56:52.650936+00
16	561	17612	225001922	2025-10-15 16:56:52.650936+00
17	562	17612	225001924	2025-10-15 16:56:52.650936+00
18	563	17612	225001930	2025-10-15 16:56:52.650936+00
19	564	17612	225001932	2025-10-15 16:56:52.650936+00
20	587	17612	225060656	2025-10-15 16:56:52.650936+00
21	587	17914	225060656	2025-10-15 16:56:52.650936+00
22	566	17612	225003323	2025-10-15 16:56:52.650936+00
23	567	17612	225003324	2025-10-15 16:56:52.650936+00
24	568	17612	225003326	2025-10-15 16:56:52.650936+00
25	569	17612	225003328	2025-10-15 16:56:52.650936+00
26	570	17612	225003334	2025-10-15 16:56:52.650936+00
27	571	17612	225004497	2025-10-15 16:56:52.650936+00
28	573	17612	225004504	2025-10-15 16:56:52.650936+00
29	574	17612	225004506	2025-10-15 16:56:52.650936+00
30	575	17612	225004508	2025-10-15 16:56:52.650936+00
31	576	17612	225004509	2025-10-15 16:56:52.650936+00
32	579	17612	225004518	2025-10-15 16:56:52.650936+00
33	585	17612	225005536	2025-10-15 16:56:52.650936+00
34	586	17612	225005538	2025-10-15 16:56:52.650936+00
35	588	17612	225005542	2025-10-15 16:56:52.650936+00
36	589	17612	225005543	2025-10-15 16:56:52.650936+00
37	597	17612	225006651	2025-10-15 16:56:52.650936+00
38	598	17612	225006655	2025-10-15 16:56:52.650936+00
39	565	17612	225001934	2025-10-15 16:56:52.650936+00
40	578	17612	225004515	2025-10-15 16:56:52.650936+00
41	544	18795	224979931	2025-10-15 16:56:52.650936+00
42	545	17612	224998139	2025-10-15 16:56:52.650936+00
43	590	17612	225006627	2025-10-15 16:56:52.650936+00
44	591	17612	225006630	2025-10-15 16:56:52.650936+00
45	592	17612	225006633	2025-10-15 16:56:52.650936+00
46	593	17612	225006636	2025-10-15 16:56:52.650936+00
47	594	17612	225006638	2025-10-15 16:56:52.650936+00
48	595	17612	225060528	2025-10-15 16:56:52.650936+00
49	595	17914	225060528	2025-10-15 16:56:52.650936+00
50	596	17612	225006644	2025-10-15 16:56:52.650936+00
51	580	17612	225005520	2025-10-15 16:56:52.650936+00
52	581	17612	225005523	2025-10-15 16:56:52.650936+00
53	582	17612	225005526	2025-10-15 16:56:52.650936+00
54	583	17612	225005528	2025-10-15 16:56:52.650936+00
55	584	17612	225005533	2025-10-15 16:56:52.650936+00
56	572	17612	225004501	2025-10-15 16:56:52.650936+00
57	577	17612	225004513	2025-10-15 16:56:52.650936+00
58	625	17612	225070393	2025-10-15 17:55:09.961711+00
59	626	17612	225088618	2025-10-15 17:55:09.961711+00
60	627	17612	225095066	2025-10-15 21:11:07.449497+00
61	628	17914	225102299	2025-10-15 21:11:46.116224+00
62	629	17904	225115317	2025-10-15 21:11:46.116224+00
63	630	17612	225116498	2025-10-15 21:11:46.116224+00
64	631	17612	225123499	2025-10-15 21:11:46.116224+00
65	633	17914	225097312	2025-10-15 21:16:18.609772+00
66	639	17612	225292241	2025-10-16 13:28:22.064364+00
67	640	17612	225293280	2025-10-16 13:33:30.253847+00
68	642	17612	225300112	2025-10-16 14:03:57.369212+00
69	644	17612	225326318	2025-10-16 15:40:06.854684+00
\.


--
-- Data for Name: sku_lot; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.sku_lot (id, sku, lot, active, created_at, updated_at) FROM stdin;
1	17612	250101	0	2025-10-02 06:58:13	2025-10-02 06:58:13
2	17904	240276	0	2025-10-02 06:58:13	2025-10-02 06:58:13
3	17914	240286	0	2025-10-02 06:58:13	2025-10-02 06:58:13
4	18675	240231	1	2025-10-02 06:58:13	2025-10-02 06:58:13
5	17612	250172	0	2025-10-02 06:58:13	2025-10-02 06:58:13
6	17612	250195	0	2025-10-02 06:58:13	2025-10-02 06:58:13
7	18795	11001	1	2025-10-02 06:58:13	2025-10-02 06:58:13
8	18795	11002	0	2025-10-02 06:58:13	2025-10-02 06:58:13
9	17612	250216	0	2025-10-02 06:58:13	2025-10-02 06:58:13
10	17612	250237	0	2025-10-02 06:58:13	2025-10-06 17:05:10
11	17914	250297	1	2025-10-02 06:58:13	2025-10-02 06:58:13
12	17904	250240	1	2025-10-02 06:58:13	2025-10-02 06:58:13
16	17612	250300	1	2025-10-03 20:17:08	2025-10-06 17:05:04
\.


--
-- Data for Name: sync_watermark; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.sync_watermark (id, workflow_name, last_sync_timestamp, updated_at) FROM stdin;
1	unified-shipstation-sync	2025-10-16T10:20:07.2100000	2025-10-16 17:29:44.545022+00
\.


--
-- Data for Name: system_kpis; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.system_kpis (id, snapshot_date, orders_today, shipments_sent, pending_uploads, system_status, total_revenue_cents, created_at) FROM stdin;
1	2025-10-01	0	0	0	online	0	2025-10-01 12:06:14
\.


--
-- Data for Name: weekly_shipped_history; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.weekly_shipped_history (id, start_date, end_date, sku, quantity_shipped, created_at) FROM stdin;
13	2024-09-30	2024-10-06	17612	529	2025-10-01 12:22:32
14	2024-09-30	2024-10-06	17904	41	2025-10-01 12:22:32
15	2024-09-30	2024-10-06	17914	23	2025-10-01 12:22:32
16	2024-09-30	2024-10-06	18675	2	2025-10-01 12:22:32
17	2024-09-30	2024-10-06	18795	0	2025-10-01 12:22:32
18	2024-10-07	2024-10-13	17612	725	2025-10-01 12:22:32
19	2024-10-07	2024-10-13	17904	12	2025-10-01 12:22:32
20	2024-10-07	2024-10-13	17914	38	2025-10-01 12:22:32
21	2024-10-07	2024-10-13	18675	6	2025-10-01 12:22:32
22	2024-10-07	2024-10-13	18795	0	2025-10-01 12:22:32
23	2024-10-14	2024-10-20	17612	531	2025-10-01 12:22:32
24	2024-10-14	2024-10-20	17904	16	2025-10-01 12:22:32
25	2024-10-14	2024-10-20	17914	38	2025-10-01 12:22:32
26	2024-10-14	2024-10-20	18675	8	2025-10-01 12:22:32
27	2024-10-14	2024-10-20	18795	0	2025-10-01 12:22:32
28	2024-10-21	2024-10-27	17612	508	2025-10-01 12:22:32
29	2024-10-21	2024-10-27	17904	12	2025-10-01 12:22:32
30	2024-10-21	2024-10-27	17914	22	2025-10-01 12:22:32
31	2024-10-21	2024-10-27	18675	2	2025-10-01 12:22:32
32	2024-10-21	2024-10-27	18795	0	2025-10-01 12:22:32
33	2024-10-28	2024-11-03	17612	730	2025-10-01 12:22:32
34	2024-10-28	2024-11-03	17904	20	2025-10-01 12:22:32
35	2024-10-28	2024-11-03	17914	46	2025-10-01 12:22:32
36	2024-10-28	2024-11-03	18675	7	2025-10-01 12:22:32
37	2024-10-28	2024-11-03	18795	0	2025-10-01 12:22:32
38	2024-11-04	2024-11-10	17612	508	2025-10-01 12:22:32
39	2024-11-04	2024-11-10	17904	32	2025-10-01 12:22:32
40	2024-11-04	2024-11-10	17914	38	2025-10-01 12:22:32
41	2024-11-04	2024-11-10	18675	21	2025-10-01 12:22:32
42	2024-11-04	2024-11-10	18795	0	2025-10-01 12:22:32
43	2024-11-11	2024-11-17	17612	532	2025-10-01 12:22:32
44	2024-11-11	2024-11-17	17904	5	2025-10-01 12:22:32
45	2024-11-11	2024-11-17	17914	21	2025-10-01 12:22:32
46	2024-11-11	2024-11-17	18675	15	2025-10-01 12:22:32
47	2024-11-11	2024-11-17	18795	0	2025-10-01 12:22:32
48	2024-11-18	2024-11-24	17612	466	2025-10-01 12:22:32
49	2024-11-18	2024-11-24	17904	7	2025-10-01 12:22:32
50	2024-11-18	2024-11-24	17914	14	2025-10-01 12:22:32
51	2024-11-18	2024-11-24	18675	1	2025-10-01 12:22:32
52	2024-11-18	2024-11-24	18795	0	2025-10-01 12:22:32
53	2024-11-25	2024-12-01	17612	233	2025-10-01 12:22:32
54	2024-11-25	2024-12-01	17904	10	2025-10-01 12:22:32
55	2024-11-25	2024-12-01	17914	52	2025-10-01 12:22:32
56	2024-11-25	2024-12-01	18675	0	2025-10-01 12:22:32
57	2024-11-25	2024-12-01	18795	0	2025-10-01 12:22:32
58	2024-12-02	2024-12-08	17612	245	2025-10-01 12:22:32
59	2024-12-02	2024-12-08	17904	3	2025-10-01 12:22:32
60	2024-12-02	2024-12-08	17914	10	2025-10-01 12:22:32
61	2024-12-02	2024-12-08	18675	0	2025-10-01 12:22:32
62	2024-12-02	2024-12-08	18795	0	2025-10-01 12:22:32
63	2024-12-09	2024-12-15	17612	1221	2025-10-02T03:37:00.150790
64	2024-12-09	2024-12-15	17904	9	2025-10-01 12:22:32
65	2024-12-09	2024-12-15	17914	48	2025-10-01 12:22:32
66	2024-12-09	2024-12-15	18675	0	2025-10-01 12:22:32
67	2024-12-09	2024-12-15	18795	0	2025-10-01 12:22:32
68	2024-12-16	2024-12-22	17612	582	2025-10-01 12:22:32
69	2024-12-16	2024-12-22	17904	17	2025-10-01 12:22:32
70	2024-12-16	2024-12-22	17914	46	2025-10-01 12:22:32
71	2024-12-16	2024-12-22	18675	1	2025-10-01 12:22:32
72	2024-12-16	2024-12-22	18795	0	2025-10-01 12:22:32
73	2024-12-23	2024-12-29	17612	409	2025-10-01 12:22:32
74	2024-12-23	2024-12-29	17904	13	2025-10-01 12:22:32
75	2024-12-23	2024-12-29	17914	10	2025-10-01 12:22:32
76	2024-12-23	2024-12-29	18675	1	2025-10-01 12:22:32
77	2024-12-23	2024-12-29	18795	0	2025-10-01 12:22:32
78	2024-12-30	2025-01-05	17612	187	2025-10-01 12:22:32
79	2024-12-30	2025-01-05	17904	2	2025-10-01 12:22:32
80	2024-12-30	2025-01-05	17914	3	2025-10-01 12:22:32
81	2024-12-30	2025-01-05	18675	0	2025-10-01 12:22:32
82	2024-12-30	2025-01-05	18795	0	2025-10-01 12:22:32
83	2025-01-06	2025-01-12	17612	249	2025-10-01 12:22:32
84	2025-01-06	2025-01-12	17904	14	2025-10-01 12:22:32
85	2025-01-06	2025-01-12	17914	11	2025-10-01 12:22:32
86	2025-01-06	2025-01-12	18675	0	2025-10-01 12:22:32
87	2025-01-06	2025-01-12	18795	0	2025-10-01 12:22:32
88	2025-01-13	2025-01-19	17612	536	2025-10-01 12:22:32
89	2025-01-13	2025-01-19	17904	6	2025-10-01 12:22:32
90	2025-01-13	2025-01-19	17914	31	2025-10-01 12:22:32
91	2025-01-13	2025-01-19	18675	7	2025-10-01 12:22:32
92	2025-01-13	2025-01-19	18795	0	2025-10-01 12:22:32
93	2025-01-20	2025-01-26	17612	429	2025-10-01 12:22:32
94	2025-01-20	2025-01-26	17904	13	2025-10-01 12:22:32
95	2025-01-20	2025-01-26	17914	37	2025-10-01 12:22:32
96	2025-01-20	2025-01-26	18675	0	2025-10-01 12:22:32
97	2025-01-20	2025-01-26	18795	0	2025-10-01 12:22:32
98	2025-01-27	2025-02-02	17612	424	2025-10-01 12:22:32
99	2025-01-27	2025-02-02	17904	13	2025-10-01 12:22:32
100	2025-01-27	2025-02-02	17914	21	2025-10-01 12:22:32
101	2025-01-27	2025-02-02	18675	0	2025-10-01 12:22:32
102	2025-01-27	2025-02-02	18795	0	2025-10-01 12:22:32
103	2025-02-03	2025-02-09	17612	354	2025-10-01 12:22:32
104	2025-02-03	2025-02-09	17904	21	2025-10-01 12:22:32
105	2025-02-03	2025-02-09	17914	34	2025-10-01 12:22:32
106	2025-02-03	2025-02-09	18675	7	2025-10-01 12:22:32
107	2025-02-03	2025-02-09	18795	0	2025-10-01 12:22:32
108	2025-02-10	2025-02-16	17612	486	2025-10-01 12:22:32
109	2025-02-10	2025-02-16	17904	7	2025-10-01 12:22:32
110	2025-02-10	2025-02-16	17914	28	2025-10-01 12:22:32
111	2025-02-10	2025-02-16	18675	3	2025-10-01 12:22:32
112	2025-02-10	2025-02-16	18795	0	2025-10-01 12:22:32
113	2025-02-17	2025-02-23	17612	531	2025-10-01 12:22:32
114	2025-02-17	2025-02-23	17904	11	2025-10-01 12:22:32
115	2025-02-17	2025-02-23	17914	28	2025-10-01 12:22:32
116	2025-02-17	2025-02-23	18675	0	2025-10-01 12:22:32
117	2025-02-17	2025-02-23	18795	0	2025-10-01 12:22:32
118	2025-02-24	2025-03-02	17612	355	2025-10-01 12:22:32
119	2025-02-24	2025-03-02	17904	10	2025-10-01 12:22:32
120	2025-02-24	2025-03-02	17914	34	2025-10-01 12:22:32
121	2025-02-24	2025-03-02	18675	0	2025-10-01 12:22:32
122	2025-02-24	2025-03-02	18795	0	2025-10-01 12:22:32
123	2025-03-03	2025-03-09	17612	423	2025-10-01 12:22:32
124	2025-03-03	2025-03-09	17904	17	2025-10-01 12:22:32
125	2025-03-03	2025-03-09	17914	20	2025-10-01 12:22:32
126	2025-03-03	2025-03-09	18675	7	2025-10-01 12:22:32
127	2025-03-03	2025-03-09	18795	0	2025-10-01 12:22:32
128	2025-03-10	2025-03-16	17612	519	2025-10-01 12:22:32
129	2025-03-10	2025-03-16	17904	14	2025-10-01 12:22:32
130	2025-03-10	2025-03-16	17914	23	2025-10-01 12:22:32
131	2025-03-10	2025-03-16	18675	11	2025-10-01 12:22:32
132	2025-03-10	2025-03-16	18795	0	2025-10-01 12:22:32
133	2025-03-17	2025-03-23	17612	474	2025-10-01 12:22:32
134	2025-03-17	2025-03-23	17904	11	2025-10-01 12:22:32
135	2025-03-17	2025-03-23	17914	61	2025-10-01 12:22:32
136	2025-03-17	2025-03-23	18675	1	2025-10-01 12:22:32
137	2025-03-17	2025-03-23	18795	0	2025-10-01 12:22:32
138	2025-03-24	2025-03-30	17612	417	2025-10-01 12:22:32
139	2025-03-24	2025-03-30	17904	18	2025-10-01 12:22:32
140	2025-03-24	2025-03-30	17914	5	2025-10-01 12:22:32
141	2025-03-24	2025-03-30	18675	2	2025-10-01 12:22:32
142	2025-03-24	2025-03-30	18795	0	2025-10-01 12:22:32
143	2025-03-31	2025-04-06	17612	447	2025-10-01 12:22:32
144	2025-03-31	2025-04-06	17904	5	2025-10-01 12:22:32
145	2025-03-31	2025-04-06	17914	20	2025-10-01 12:22:32
146	2025-03-31	2025-04-06	18675	1	2025-10-01 12:22:32
147	2025-03-31	2025-04-06	18795	0	2025-10-01 12:22:32
148	2025-04-07	2025-04-13	17612	455	2025-10-01 12:22:32
149	2025-04-07	2025-04-13	17904	7	2025-10-01 12:22:32
150	2025-04-07	2025-04-13	17914	34	2025-10-01 12:22:32
151	2025-04-07	2025-04-13	18675	13	2025-10-01 12:22:32
152	2025-04-07	2025-04-13	18795	0	2025-10-01 12:22:32
153	2025-04-14	2025-04-20	17612	501	2025-10-01 12:22:32
154	2025-04-14	2025-04-20	17904	8	2025-10-01 12:22:32
155	2025-04-14	2025-04-20	17914	18	2025-10-01 12:22:32
156	2025-04-14	2025-04-20	18675	3	2025-10-01 12:22:32
157	2025-04-14	2025-04-20	18795	0	2025-10-01 12:22:32
158	2025-04-21	2025-04-27	17612	518	2025-10-01 12:22:32
159	2025-04-21	2025-04-27	17904	18	2025-10-01 12:22:32
160	2025-04-21	2025-04-27	17914	22	2025-10-01 12:22:32
161	2025-04-21	2025-04-27	18675	0	2025-10-01 12:22:32
162	2025-04-21	2025-04-27	18795	0	2025-10-01 12:22:32
163	2025-04-28	2025-05-04	17612	622	2025-10-01 12:22:32
164	2025-04-28	2025-05-04	17904	16	2025-10-01 12:22:32
165	2025-04-28	2025-05-04	17914	36	2025-10-01 12:22:32
166	2025-04-28	2025-05-04	18675	1	2025-10-01 12:22:32
167	2025-04-28	2025-05-04	18795	0	2025-10-01 12:22:32
168	2025-05-05	2025-05-11	17612	479	2025-10-01 12:22:32
169	2025-05-05	2025-05-11	17904	25	2025-10-01 12:22:32
170	2025-05-05	2025-05-11	17914	17	2025-10-01 12:22:32
171	2025-05-05	2025-05-11	18675	15	2025-10-01 12:22:32
172	2025-05-05	2025-05-11	18795	0	2025-10-01 12:22:32
173	2025-05-12	2025-05-18	17612	516	2025-10-01 12:22:32
174	2025-05-12	2025-05-18	17904	16	2025-10-01 12:22:32
175	2025-05-12	2025-05-18	17914	69	2025-10-01 12:22:32
176	2025-05-12	2025-05-18	18675	2	2025-10-01 12:22:32
177	2025-05-12	2025-05-18	18795	0	2025-10-01 12:22:32
178	2025-05-19	2025-05-25	17612	497	2025-10-01 12:22:32
179	2025-05-19	2025-05-25	17904	16	2025-10-01 12:22:32
180	2025-05-19	2025-05-25	17914	30	2025-10-01 12:22:32
181	2025-05-19	2025-05-25	18675	0	2025-10-01 12:22:32
182	2025-05-19	2025-05-25	18795	0	2025-10-01 12:22:32
183	2025-05-26	2025-06-01	17612	334	2025-10-01 12:22:32
184	2025-05-26	2025-06-01	17904	4	2025-10-01 12:22:32
185	2025-05-26	2025-06-01	17914	21	2025-10-01 12:22:32
186	2025-05-26	2025-06-01	18675	5	2025-10-01 12:22:32
187	2025-05-26	2025-06-01	18795	0	2025-10-01 12:22:32
188	2025-06-02	2025-06-08	17612	697	2025-10-01 12:22:32
189	2025-06-02	2025-06-08	17904	25	2025-10-01 12:22:32
190	2025-06-02	2025-06-08	17914	24	2025-10-01 12:22:32
191	2025-06-02	2025-06-08	18675	2	2025-10-01 12:22:32
192	2025-06-02	2025-06-08	18795	0	2025-10-01 12:22:32
193	2025-06-09	2025-06-15	17612	518	2025-10-01 12:22:32
194	2025-06-09	2025-06-15	17904	18	2025-10-01 12:22:32
195	2025-06-09	2025-06-15	17914	32	2025-10-01 12:22:32
196	2025-06-09	2025-06-15	18675	2	2025-10-01 12:22:32
197	2025-06-09	2025-06-15	18795	0	2025-10-01 12:22:32
198	2025-06-16	2025-06-22	17612	400	2025-10-01 12:22:32
199	2025-06-16	2025-06-22	17904	7	2025-10-01 12:22:32
200	2025-06-16	2025-06-22	17914	27	2025-10-01 12:22:32
201	2025-06-16	2025-06-22	18675	16	2025-10-01 12:22:32
202	2025-06-16	2025-06-22	18795	0	2025-10-01 12:22:32
203	2025-06-23	2025-06-29	17612	347	2025-10-01 12:22:32
204	2025-06-23	2025-06-29	17904	13	2025-10-01 12:22:32
205	2025-06-23	2025-06-29	17914	20	2025-10-01 12:22:32
206	2025-06-23	2025-06-29	18675	0	2025-10-01 12:22:32
207	2025-06-23	2025-06-29	18795	0	2025-10-01 12:22:32
208	2025-06-30	2025-07-06	17612	569	2025-10-01 12:22:32
209	2025-06-30	2025-07-06	17904	7	2025-10-01 12:22:32
210	2025-06-30	2025-07-06	17914	32	2025-10-01 12:22:32
211	2025-06-30	2025-07-06	18675	0	2025-10-01 12:22:32
212	2025-06-30	2025-07-06	18795	0	2025-10-01 12:22:32
213	2025-07-07	2025-07-13	17612	379	2025-10-01 12:22:32
214	2025-07-07	2025-07-13	17904	17	2025-10-01 12:22:32
215	2025-07-07	2025-07-13	17914	18	2025-10-01 12:22:32
216	2025-07-07	2025-07-13	18675	2	2025-10-01 12:22:32
217	2025-07-07	2025-07-13	18795	3	2025-10-01 12:22:32
218	2025-07-14	2025-07-20	17612	514	2025-10-01 12:22:32
219	2025-07-14	2025-07-20	17904	18	2025-10-01 12:22:32
220	2025-07-14	2025-07-20	17914	20	2025-10-01 12:22:32
221	2025-07-14	2025-07-20	18675	2	2025-10-01 12:22:32
222	2025-07-14	2025-07-20	18795	1	2025-10-01 12:22:32
223	2025-07-21	2025-07-27	17612	483	2025-10-01 12:22:32
224	2025-07-21	2025-07-27	17904	15	2025-10-01 12:22:32
225	2025-07-21	2025-07-27	17914	19	2025-10-01 12:22:32
226	2025-07-21	2025-07-27	18675	1	2025-10-01 12:22:32
227	2025-07-21	2025-07-27	18795	9	2025-10-01 12:22:32
228	2025-07-28	2025-08-03	17612	308	2025-10-01 12:22:32
229	2025-07-28	2025-08-03	17904	1	2025-10-01 12:22:32
230	2025-07-28	2025-08-03	17914	13	2025-10-01 12:22:32
231	2025-07-28	2025-08-03	18675	6	2025-10-01 12:22:32
232	2025-07-28	2025-08-03	18795	14	2025-10-01 12:22:32
233	2025-08-04	2025-08-10	17612	456	2025-10-01 12:22:32
234	2025-08-04	2025-08-10	17904	12	2025-10-01 12:22:32
235	2025-08-04	2025-08-10	17914	31	2025-10-01 12:22:32
236	2025-08-04	2025-08-10	18675	3	2025-10-01 12:22:32
237	2025-08-04	2025-08-10	18795	16	2025-10-01 12:22:32
238	2025-08-11	2025-08-17	17612	531	2025-10-01 12:22:32
239	2025-08-11	2025-08-17	17904	15	2025-10-01 12:22:32
240	2025-08-11	2025-08-17	17914	29	2025-10-01 12:22:32
241	2025-08-11	2025-08-17	18675	10	2025-10-01 12:22:32
242	2025-08-11	2025-08-17	18795	9	2025-10-01 12:22:32
243	2025-08-18	2025-08-24	17612	463	2025-10-01 12:22:32
244	2025-08-18	2025-08-24	17904	14	2025-10-01 12:22:32
245	2025-08-18	2025-08-24	17914	23	2025-10-01 12:22:32
246	2025-08-18	2025-08-24	18675	10	2025-10-01 12:22:32
247	2025-08-18	2025-08-24	18795	6	2025-10-01 12:22:32
248	2025-08-25	2025-08-31	17612	336	2025-10-01 12:22:32
249	2025-08-25	2025-08-31	17904	9	2025-10-01 12:22:32
250	2025-08-25	2025-08-31	17914	11	2025-10-01 12:22:32
251	2025-08-25	2025-08-31	18675	0	2025-10-01 12:22:32
252	2025-08-25	2025-08-31	18795	13	2025-10-01 12:22:32
253	2025-09-01	2025-09-07	17612	419	2025-10-01 12:22:32
254	2025-09-01	2025-09-07	17904	10	2025-10-01 12:22:32
255	2025-09-01	2025-09-07	17914	15	2025-10-01 12:22:32
256	2025-09-01	2025-09-07	18675	0	2025-10-01 12:22:32
257	2025-09-01	2025-09-07	18795	13	2025-10-01 12:22:32
258	2025-09-08	2025-09-14	17612	480	2025-10-01 12:22:32
259	2025-09-08	2025-09-14	17904	1	2025-10-01 12:22:32
260	2025-09-08	2025-09-14	17914	69	2025-10-01 12:22:32
261	2025-09-08	2025-09-14	18675	0	2025-10-01 12:22:32
262	2025-09-08	2025-09-14	18795	7	2025-10-01 12:22:32
263	2025-09-15	2025-09-21	17612	632	2025-10-01 12:22:32
264	2025-09-15	2025-09-21	17904	28	2025-10-01 12:22:32
265	2025-09-15	2025-09-21	17914	22	2025-10-01 12:22:32
266	2025-09-15	2025-09-21	18675	1	2025-10-01 12:22:32
267	2025-09-15	2025-09-21	18795	16	2025-10-01 12:22:32
268	2025-09-22	2025-09-28	17612	582	2025-10-01 12:22:32
269	2025-09-22	2025-09-28	17904	18	2025-10-01 12:22:32
270	2025-09-22	2025-09-28	17914	28	2025-10-01 12:22:32
271	2025-09-22	2025-09-28	18675	0	2025-10-01 12:22:32
272	2025-09-22	2025-09-28	18795	9	2025-10-01 12:22:32
273	2025-09-29	2025-10-05	17612	400	2025-10-06 16:07:45
274	2025-09-29	2025-10-05	17904	3	2025-10-06 16:07:45
275	2025-09-29	2025-10-05	17914	18	2025-10-06 16:07:45
276	2025-09-29	2025-10-05	18675	1	2025-10-06 17:56:08
277	2025-09-29	2025-10-05	18795	8	2025-10-06 16:07:45
278	2025-10-06	2025-10-12	17612	896	2025-10-15 21:29:08.23869+00
279	2025-10-06	2025-10-12	17904	18	2025-10-15 21:29:08.23869+00
280	2025-10-06	2025-10-12	17914	60	2025-10-15 21:29:08.23869+00
281	2025-10-06	2025-10-12	18795	35	2025-10-15 21:29:08.23869+00
\.


--
-- Data for Name: workflow_controls; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.workflow_controls (workflow_name, enabled, last_updated, updated_by, last_run_at) FROM stdin;
unified-shipstation-sync	t	2025-10-16 14:49:24.417779	admin	2025-10-16 17:29:43.825594
shipstation-upload	t	2025-10-16 14:49:23.969091	admin	2025-10-16 17:30:34.110086
xml-import	t	2025-10-16 14:49:27.241303	admin	2025-10-16 17:32:54.608519
orders-cleanup	t	2025-10-16 14:49:23.460803	admin	2025-10-16 14:12:50.161686
weekly-reporter	t	2025-10-16 14:49:24.911886	admin	2025-10-15 21:28:35.974099
\.


--
-- Data for Name: workflows; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.workflows (id, name, display_name, status, last_run_at, duration_seconds, records_processed, details, enabled, created_at, updated_at) FROM stdin;
1	daily_shipment_processor	Daily Shipment Processor	running	2025-10-15 21:28:31.949378+00	\N	\N	\N	1	2025-10-15 19:53:51.273111+00	2025-10-15 19:53:51.273111+00
\.


--
-- Name: bundle_components_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.bundle_components_id_seq', 57, false);


--
-- Name: bundle_skus_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.bundle_skus_id_seq', 52, false);


--
-- Name: configuration_params_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.configuration_params_id_seq', 60, false);


--
-- Name: inventory_current_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.inventory_current_id_seq', 40, true);


--
-- Name: inventory_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.inventory_transactions_id_seq', 75, true);


--
-- Name: lot_inventory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.lot_inventory_id_seq', 1, false);


--
-- Name: order_items_inbox_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.order_items_inbox_id_seq', 43798, true);


--
-- Name: orders_inbox_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.orders_inbox_id_seq', 645, true);


--
-- Name: shipped_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.shipped_items_id_seq', 21862, true);


--
-- Name: shipped_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.shipped_orders_id_seq', 19456, true);


--
-- Name: shipping_violations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.shipping_violations_id_seq', 7, false);


--
-- Name: shipstation_metrics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.shipstation_metrics_id_seq', 282, true);


--
-- Name: shipstation_order_line_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.shipstation_order_line_items_id_seq', 69, true);


--
-- Name: sku_lot_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.sku_lot_id_seq', 17, false);


--
-- Name: sync_watermark_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.sync_watermark_id_seq', 318, true);


--
-- Name: system_kpis_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.system_kpis_id_seq', 2, false);


--
-- Name: weekly_shipped_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.weekly_shipped_history_id_seq', 285, true);


--
-- Name: workflows_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.workflows_id_seq', 6, true);


--
-- Name: bundle_components bundle_components_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.bundle_components
    ADD CONSTRAINT bundle_components_pkey PRIMARY KEY (id);


--
-- Name: bundle_skus bundle_skus_bundle_sku_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.bundle_skus
    ADD CONSTRAINT bundle_skus_bundle_sku_key UNIQUE (bundle_sku);


--
-- Name: bundle_skus bundle_skus_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.bundle_skus
    ADD CONSTRAINT bundle_skus_pkey PRIMARY KEY (id);


--
-- Name: configuration_params configuration_params_category_parameter_name_sku_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.configuration_params
    ADD CONSTRAINT configuration_params_category_parameter_name_sku_key UNIQUE (category, parameter_name, sku);


--
-- Name: configuration_params configuration_params_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.configuration_params
    ADD CONSTRAINT configuration_params_pkey PRIMARY KEY (id);


--
-- Name: inventory_current inventory_current_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.inventory_current
    ADD CONSTRAINT inventory_current_pkey PRIMARY KEY (id);


--
-- Name: inventory_current inventory_current_sku_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.inventory_current
    ADD CONSTRAINT inventory_current_sku_key UNIQUE (sku);


--
-- Name: inventory_transactions inventory_transactions_date_sku_transaction_type_quantity_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.inventory_transactions
    ADD CONSTRAINT inventory_transactions_date_sku_transaction_type_quantity_key UNIQUE (date, sku, transaction_type, quantity);


--
-- Name: inventory_transactions inventory_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.inventory_transactions
    ADD CONSTRAINT inventory_transactions_pkey PRIMARY KEY (id);


--
-- Name: lot_inventory lot_inventory_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lot_inventory
    ADD CONSTRAINT lot_inventory_pkey PRIMARY KEY (id);


--
-- Name: lot_inventory lot_inventory_sku_lot_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lot_inventory
    ADD CONSTRAINT lot_inventory_sku_lot_key UNIQUE (sku, lot);


--
-- Name: order_items_inbox order_items_inbox_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.order_items_inbox
    ADD CONSTRAINT order_items_inbox_pkey PRIMARY KEY (id);


--
-- Name: orders_inbox orders_inbox_order_number_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders_inbox
    ADD CONSTRAINT orders_inbox_order_number_key UNIQUE (order_number);


--
-- Name: orders_inbox orders_inbox_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders_inbox
    ADD CONSTRAINT orders_inbox_pkey PRIMARY KEY (id);


--
-- Name: shipped_items shipped_items_order_number_base_sku_sku_lot_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipped_items
    ADD CONSTRAINT shipped_items_order_number_base_sku_sku_lot_key UNIQUE (order_number, base_sku, sku_lot);


--
-- Name: shipped_items shipped_items_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipped_items
    ADD CONSTRAINT shipped_items_pkey PRIMARY KEY (id);


--
-- Name: shipped_orders shipped_orders_order_number_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipped_orders
    ADD CONSTRAINT shipped_orders_order_number_key UNIQUE (order_number);


--
-- Name: shipped_orders shipped_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipped_orders
    ADD CONSTRAINT shipped_orders_pkey PRIMARY KEY (id);


--
-- Name: shipping_violations shipping_violations_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipping_violations
    ADD CONSTRAINT shipping_violations_pkey PRIMARY KEY (id);


--
-- Name: shipstation_metrics shipstation_metrics_metric_name_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipstation_metrics
    ADD CONSTRAINT shipstation_metrics_metric_name_key UNIQUE (metric_name);


--
-- Name: shipstation_metrics shipstation_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipstation_metrics
    ADD CONSTRAINT shipstation_metrics_pkey PRIMARY KEY (id);


--
-- Name: shipstation_order_line_items shipstation_order_line_items_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipstation_order_line_items
    ADD CONSTRAINT shipstation_order_line_items_pkey PRIMARY KEY (id);


--
-- Name: sku_lot sku_lot_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sku_lot
    ADD CONSTRAINT sku_lot_pkey PRIMARY KEY (id);


--
-- Name: sku_lot sku_lot_sku_lot_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sku_lot
    ADD CONSTRAINT sku_lot_sku_lot_key UNIQUE (sku, lot);


--
-- Name: sync_watermark sync_watermark_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sync_watermark
    ADD CONSTRAINT sync_watermark_pkey PRIMARY KEY (id);


--
-- Name: sync_watermark sync_watermark_workflow_name_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sync_watermark
    ADD CONSTRAINT sync_watermark_workflow_name_key UNIQUE (workflow_name);


--
-- Name: system_kpis system_kpis_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.system_kpis
    ADD CONSTRAINT system_kpis_pkey PRIMARY KEY (id);


--
-- Name: system_kpis system_kpis_snapshot_date_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.system_kpis
    ADD CONSTRAINT system_kpis_snapshot_date_key UNIQUE (snapshot_date);


--
-- Name: weekly_shipped_history weekly_shipped_history_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.weekly_shipped_history
    ADD CONSTRAINT weekly_shipped_history_pkey PRIMARY KEY (id);


--
-- Name: weekly_shipped_history weekly_shipped_history_start_date_end_date_sku_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.weekly_shipped_history
    ADD CONSTRAINT weekly_shipped_history_start_date_end_date_sku_key UNIQUE (start_date, end_date, sku);


--
-- Name: workflow_controls workflow_controls_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.workflow_controls
    ADD CONSTRAINT workflow_controls_pkey PRIMARY KEY (workflow_name);


--
-- Name: workflows workflows_name_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_name_key UNIQUE (name);


--
-- Name: workflows workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_pkey PRIMARY KEY (id);


--
-- Name: idx_bundle_components_bundle; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_bundle_components_bundle ON public.bundle_components USING btree (bundle_sku_id);


--
-- Name: idx_bundle_components_sku; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_bundle_components_sku ON public.bundle_components USING btree (component_sku);


--
-- Name: idx_bundle_skus_active; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_bundle_skus_active ON public.bundle_skus USING btree (active);


--
-- Name: idx_config_category; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_config_category ON public.configuration_params USING btree (category);


--
-- Name: idx_config_sku; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_config_sku ON public.configuration_params USING btree (sku);


--
-- Name: idx_inv_trans_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_inv_trans_date ON public.inventory_transactions USING btree (date);


--
-- Name: idx_inv_trans_sku_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_inv_trans_sku_date ON public.inventory_transactions USING btree (sku, date);


--
-- Name: idx_inv_trans_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_inv_trans_type ON public.inventory_transactions USING btree (transaction_type);


--
-- Name: idx_inventory_current_alert; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_inventory_current_alert ON public.inventory_current USING btree (alert_level);


--
-- Name: idx_order_items_inbox_order; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_order_items_inbox_order ON public.order_items_inbox USING btree (order_inbox_id);


--
-- Name: idx_order_items_inbox_sku; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_order_items_inbox_sku ON public.order_items_inbox USING btree (sku);


--
-- Name: idx_shipped_items_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_shipped_items_date ON public.shipped_items USING btree (ship_date);


--
-- Name: idx_shipped_items_order; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_shipped_items_order ON public.shipped_items USING btree (order_number);


--
-- Name: idx_shipped_items_sku_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_shipped_items_sku_date ON public.shipped_items USING btree (base_sku, ship_date);


--
-- Name: idx_shipped_orders_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_shipped_orders_date ON public.shipped_orders USING btree (ship_date);


--
-- Name: idx_shipstation_order_line_items_unique; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX idx_shipstation_order_line_items_unique ON public.shipstation_order_line_items USING btree (order_inbox_id, sku);


--
-- Name: idx_violations_order; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_violations_order ON public.shipping_violations USING btree (order_id);


--
-- Name: idx_violations_resolved; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_violations_resolved ON public.shipping_violations USING btree (is_resolved, detected_at);


--
-- Name: idx_violations_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_violations_type ON public.shipping_violations USING btree (violation_type);


--
-- Name: idx_weekly_history_dates; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_weekly_history_dates ON public.weekly_shipped_history USING btree (start_date, end_date);


--
-- Name: idx_weekly_history_sku_start; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_weekly_history_sku_start ON public.weekly_shipped_history USING btree (sku, start_date);


--
-- Name: idx_workflows_enabled; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_workflows_enabled ON public.workflows USING btree (enabled);


--
-- Name: idx_workflows_last_run; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_workflows_last_run ON public.workflows USING btree (status, last_run_at);


--
-- Name: idx_workflows_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_workflows_status ON public.workflows USING btree (status, enabled);


--
-- Name: uniq_shipped_items_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX uniq_shipped_items_key ON public.shipped_items USING btree (order_number, base_sku, sku_lot);


--
-- Name: bundle_components bundle_components_bundle_sku_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.bundle_components
    ADD CONSTRAINT bundle_components_bundle_sku_id_fkey FOREIGN KEY (bundle_sku_id) REFERENCES public.bundle_skus(id) ON DELETE CASCADE;


--
-- Name: order_items_inbox order_items_inbox_order_inbox_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.order_items_inbox
    ADD CONSTRAINT order_items_inbox_order_inbox_id_fkey FOREIGN KEY (order_inbox_id) REFERENCES public.orders_inbox(id) ON DELETE CASCADE;


--
-- Name: shipped_items shipped_items_order_number_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipped_items
    ADD CONSTRAINT shipped_items_order_number_fkey FOREIGN KEY (order_number) REFERENCES public.shipped_orders(order_number);


--
-- Name: shipping_violations shipping_violations_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipping_violations
    ADD CONSTRAINT shipping_violations_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders_inbox(id) ON DELETE CASCADE;


--
-- Name: shipstation_order_line_items shipstation_order_line_items_order_inbox_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipstation_order_line_items
    ADD CONSTRAINT shipstation_order_line_items_order_inbox_id_fkey FOREIGN KEY (order_inbox_id) REFERENCES public.orders_inbox(id);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION;


--
-- PostgreSQL database dump complete
--

