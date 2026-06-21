import unittest
from war_report import calculate_final_payouts

class TestPayoutCalculations(unittest.TestCase):

    def setUp(self):
        """Set up common data for tests."""
        self.member_stats = [
            ('1', {'name': 'Member A', 'respect_gained': 100.0, 'base_respect_gained': 80.0, 'hits_made': 10, 'assists': 2, 'hits_taken': 5, 'defends': 1, 'stalemates': 0}),
            ('2', {'name': 'Member B', 'respect_gained': 200.0, 'base_respect_gained': 160.0, 'hits_made': 20, 'assists': 4, 'hits_taken': 10, 'defends': 2, 'stalemates': 1}),
            ('3', {'name': 'Member C', 'respect_gained': 50.0, 'base_respect_gained': 40.0, 'hits_made': 5, 'assists': 1, 'hits_taken': 2, 'defends': 0, 'stalemates': 0}),
        ]
        self.prize_total = "1000000000"
        self.faction_share = "10"
        self.guaranteed_share = "20"

    def test_simple_payout(self):
        """Test a simple payout calculation with no special settings."""
        settings = {}
        result = calculate_final_payouts(settings, self.member_stats, self.prize_total, self.faction_share, self.guaranteed_share)
        
        # Expected values
        # prize_total = 1,000,000,000
        # faction_take = 100,000,000
        # member_pool = 900,000,000
        # guaranteed_pool = 180,000,000 (20% of member_pool)
        # participation_pool = 720,000,000
        # guaranteed_payout_per_member = 60,000,000
        # total_respect_to_share = 350.0
        
        # Member A: 60,000,000 + (720,000,000 * 100/350) = 265,714,285.71
        # Member B: 60,000,000 + (720,000,000 * 200/350) = 471,428,571.42
        # Member C: 60,000,000 + (720,000,000 * 50/350)  = 162,857,142.85
        
        payouts = {member_id: stats['final_payout'] for member_id, stats in result}
        
        self.assertAlmostEqual(round(payouts['1'], 2), 265714285.71)
        self.assertAlmostEqual(round(payouts['2'], 2), 471428571.43)
        self.assertAlmostEqual(round(payouts['3'], 2), 162857142.86)

    def test_assist_bonus_payout(self):
        """Test payout with a flat assist bonus."""
        settings = {
            'assist_payment_type': 'flat',
            'assist_payment_value': '1000000'
        }
        result = calculate_final_payouts(settings, self.member_stats, self.prize_total, self.faction_share, self.guaranteed_share)
        
        # total_assists = 7
        # total_assist_payout = 7,000,000
        # participation_pool = 720,000,000 - 7,000,000 = 713,000,000
        
        # Member A assist_payout = 2,000,000
        # Member B assist_payout = 4,000,000
        # Member C assist_payout = 1,000,000
        
        # Member A: 60,000,000 + (713,000,000 * 100/350) + 2,000,000 = 265,714,285.71 -> 265,714,285.71
        # ??? The original calculation is wrong
        # My calculation: 60,000,000 + 203,714,285.71 + 2,000,000 = 265,714,285.71
        # Let's re-calculate
        # Member A participation: 713,000,000 * 100/350 = 203,714,285.71
        # Member A total: 60,000,000 + 203,714,285.71 + 2,000,000 = 265,714,285.71
        
        payouts = {member_id: stats['final_payout'] for member_id, stats in result}
        
        self.assertAlmostEqual(round(payouts['1'], 2), 265714285.71)
        self.assertAlmostEqual(round(payouts['2'], 2), 471428571.43)
        self.assertAlmostEqual(round(payouts['3'], 2), 162857142.86)

    def test_hit_penalty_payout(self):
        """Test payout with a penalty for hits taken."""
        settings = {
            'penalty_per_hit_taken': '500000'
        }
        result = calculate_final_payouts(settings, self.member_stats, "1000000000", "10", "20")
        
        # total_hits_taken = 17
        # total_penalty_deductions = 8,500,000
        # participation_pool = 720,000,000 - 8,500,000 = 711,500,000

        # Member A penalty = 2,500,000
        # Member B penalty = 5,000,000
        # Member C penalty = 1,000,000

        payouts = {member_id: stats['final_payout'] for member_id, stats in result}

        self.assertAlmostEqual(round(payouts['1'], 2), 260785714.29)
        self.assertAlmostEqual(round(payouts['2'], 2), 461571428.57)
        self.assertAlmostEqual(round(payouts['3'], 2), 160642857.14)

if __name__ == '__main__':
    unittest.main()
