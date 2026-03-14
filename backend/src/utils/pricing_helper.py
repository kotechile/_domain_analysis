def calculate_credit_cost(
    base_api_cost: float, 
    target_margin: float = 2.0, 
    volatility_buffer: float = 0.20
) -> float:
    """
    Calculate the credit cost to charge the user to ensure profit targets are met.
    
    This follows the formula:
    Credit Cost = (Base Cost * Target Margin) * (1 + Volatility Buffer)
    
    Args:
        base_api_cost (float): The raw cost from the API (e.g., DataForSEO or LLM cost).
        target_margin (float): The desired profit multiplier (default 2.0x).
        volatility_buffer (float): Additional buffer percentage to cover failed calls, 
                                 payment fees, and overhead (default 0.20 = 20%).
                                 
    Returns:
        float: The suggested credit cost, rounded to 2 decimal places.
    """
    # 1. Apply target margin (e.g., 2x or 3x cost)
    marign_cost = base_api_cost * target_margin
    
    # 2. Add volatility buffer (e.g., 20% for Stripe fees, failed calls, hosting)
    # The user suggested: "If an LLM call costs you $0.05, price it at $0.15–$0.20 in credits."
    # Let's see: ($0.05 * 2.0) * (1 + 0.20) = $0.12 (A bit lower than suggested $0.15-$0.2).
    # If target_margin is 3.0: ($0.05 * 3.0) * (1 + 0.20) = $0.18 (Right in the range).
    
    total_suggested = marign_cost * (1 + volatility_buffer)
    
    # Round to cents (or credits if 1 credit = $1.00)
    return round(total_suggested, 2)

if __name__ == "__main__":
    # Test cases based on user request
    print(f"Stats Sync (Base cost $0.03): {calculate_credit_cost(0.03, target_margin=2.0)}")
    print(f"LLM Call (Base cost $0.05): {calculate_credit_cost(0.05, target_margin=3.0)}")
    print(f"Deep Analysis (Base cost $0.30): {calculate_credit_cost(0.30, target_margin=2.5)}")
