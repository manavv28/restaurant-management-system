import Link from 'next/link';
export const metadata={title:'How search works · BiteAI',description:'Learn how to find restaurant menu matches near your chosen Mumbai location.'};

const steps=[
 {title:'Tell us what you’re craving',text:'Type your request or use voice search where your browser supports it. Include a dish, cuisine or budget—for example, “Hakka noodles under ₹300 within 2 km.”'},
 {title:'Choose your location and budget',text:'Select a Mumbai area or share your location. Check the search filters before exploring. Distances are straight-line estimates, not walking routes or delivery coverage.'},
 {title:'Explore matching menu options',text:'We match available catalog records to your dish, listed item price and radius. Each result shows its source and observation date where available.'},
 {title:'Check the details and your rewards',text:'Open a menu, call the restaurant or get directions. Sign in to see eligible restaurant offers and their terms. Query-based offers do not require payment-data consent.'},
];
export default function HowSearchWorks(){
 return <main className="workspace search-explainer"><Link className="secondary" href="/">← Back to BiteAI</Link><div className="eyebrow">FROM CRAVING TO CHOICE</div><h1>How your search works</h1><p className="explainer-intro">Tell us what sounds good. We’ll help you explore listed menus near your chosen location.</p><ol className="search-steps">{steps.map((step,index)=><li key={step.title}><span className="step-number" aria-hidden="true">{index+1}</span><h2>{step.title}</h2><p>{step.text}</p></li>)}</ol><section className="panel"><h2>Before you decide</h2><p>Mumbai coverage is partial. A missing result can mean missing menu data. Listed prices may have changed; confirm availability and the final total, including taxes and fees, with the restaurant.</p><p>Zomato and Swiggy search links open those platforms. They do not establish a live price comparison. Spend-based rewards use eligible verified BiteAI payment records when configured; BiteAI cannot read your GPay or UPI history.</p></section><Link className="primary explainer-cta" href="/concierge">Find my food →</Link></main>;
}
