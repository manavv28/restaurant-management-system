ALTER TABLE public.transactions ADD COLUMN refunded_paise integer NOT NULL DEFAULT 0;
ALTER TABLE public.transactions ADD COLUMN disputed boolean NOT NULL DEFAULT false;
ALTER TABLE public.transactions ADD COLUMN dispute_updated_at integer NOT NULL DEFAULT 0;
CREATE TABLE public.payment_adjustments (
 id serial PRIMARY KEY,
 transaction_id integer NOT NULL REFERENCES public.transactions(id) ON DELETE CASCADE,
 reference varchar(180) NOT NULL UNIQUE,
 kind varchar(40) NOT NULL,
 amount_paise integer NOT NULL,
 created_at varchar(40) NOT NULL
);
CREATE INDEX ix_payment_adjustments_transaction_id ON public.payment_adjustments(transaction_id);
ALTER TABLE public.payment_adjustments ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.payment_adjustments FROM PUBLIC,anon,authenticated;
