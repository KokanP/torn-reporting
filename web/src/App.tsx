import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Calculator, Shield, Target, TrendingUp, Handshake, Download, Settings, Loader2, User, ArrowLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Configure axios defaults to send credentials (cookies)
axios.defaults.withCredentials = true;

// Helper to format money
const formatMoney = (val: number) => {
  return '$' + val.toLocaleString('en-US', { maximumFractionDigits: 0 });
};

// ==================== LOGIN VIEW ====================
interface LoginViewProps {
  setUser: (user: any) => void;
  navigateTo: (path: string) => void;
}

const LoginView: React.FC<LoginViewProps> = ({ setUser, navigateTo }) => {
  const [loggingIn, setLoggingIn] = useState(false);

  const handleGoogleLogin = async () => {
    setLoggingIn(true);
    console.log('FRONTEND: handleGoogleLogin called');
    try {
      const response = await axios.post('/api/auth/google/mock', {
        email: `test_user_${Date.now()}@local.dev`,
        given_name: 'Test',
        family_name: 'User'
      });
      console.log('FRONTEND: Google mock login response:', response.data);
      if (response.data.status === 'success') {
        setUser(response.data.profile);
        if (!response.data.profile.nickname) {
          console.log('FRONTEND: Nickname is missing, redirecting to onboarding');
          navigateTo('/onboarding');
        } else {
          console.log('FRONTEND: Nickname exists, redirecting to dashboard');
          navigateTo('/');
        }
      }
    } catch (err: any) {
      console.error('FRONTEND: Google login failed:', err.response?.data || err.message);
    } finally {
      setLoggingIn(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0b1120] text-slate-300 px-4">
      <div className="w-full max-w-md bg-slate-900/85 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur-md relative overflow-hidden text-center space-y-6">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500" />
        
        <div className="mx-auto w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
          <Calculator className="w-8 h-8" />
        </div>

        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Torn War Reporter</h1>
          <p className="text-slate-400 text-sm mt-1.5">Sign in to manage payouts and settings</p>
        </div>

        <button
          onClick={handleGoogleLogin}
          disabled={loggingIn}
          className="w-full py-3.5 bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 font-bold rounded-lg transition-all flex justify-center items-center gap-3 shadow-lg hover:shadow-cyan-500/5 group cursor-pointer"
        >
          {loggingIn ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              <svg className="w-5 h-5 group-hover:scale-105 transition-transform" viewBox="0 0 24 24" width="24" height="24" xmlns="http://www.w3.org/2000/svg">
                <g transform="matrix(1, 0, 0, 1, 0, 0)">
                  <path d="M21.35,11.1H12v2.7h5.38c-0.24,1.28 -0.96,2.37 -2.04,3.1v2.58h3.3c1.93,-1.78 3.04,-4.4 3.04,-7.4C21.68,11.77 21.56,11.4 21.35,11.1z" fill="#4285F4" />
                  <path d="M12,20.6c2.43,0 4.47,-0.8 5.96,-2.2l-3.3,-2.58c-0.92,0.62 -2.1,0.98 -3.36,0.98 -2.43,0 -4.5,-1.64 -5.24,-3.84H2.66v2.66C4.14,18.57 7.82,20.6 12,20.6z" fill="#34A853" />
                  <path d="M6.76,12.96c-0.19,-0.57 -0.3,-1.18 -0.3,-1.8c0,-0.62 0.11,-1.23 0.3,-1.8V6.7H2.66c-0.64,1.28 -1,2.72 -1,4.26c0,1.54 0.36,2.98 1,4.26L6.76,12.96z" fill="#FBBC05" />
                  <path d="M12,6.12c1.32,0 2.5,0.45 3.44,1.35l2.58,-2.58C16.46,3.47 14.42,2.6 12,2.6 7.82,2.6 4.14,4.63 2.66,7.56L6.76,10.22C7.5,8.02 9.57,6.12 12,6.12z" fill="#EA4335" />
                </g>
              </svg>
              <span>Login with Google</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

// ==================== ONBOARDING VIEW ====================
interface OnboardingViewProps {
  setUser: (user: any) => void;
  navigateTo: (path: string) => void;
}

const OnboardingView: React.FC<OnboardingViewProps> = ({ setUser, navigateTo }) => {
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('FRONTEND: onboarding handleSave called with nickname:', nickname);
    if (!nickname.trim()) {
      setError('Nickname is required');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const response = await axios.post('/api/profile/update', { nickname });
      console.log('FRONTEND: onboarding save response:', response.data);
      if (response.data.status === 'success') {
        setUser(response.data.profile);
        console.log('FRONTEND: Onboarding complete, navigating to /');
        navigateTo('/');
      }
    } catch (err: any) {
      console.error('FRONTEND: onboarding save error:', err.response?.data || err.message);
      setError(err.response?.data?.error || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0b1120] text-slate-300 px-4">
      <div className="w-full max-w-md bg-slate-900/80 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur-md relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500" />
        <h1 className="text-2xl font-extrabold text-white mb-2 text-center tracking-tight">Complete Your Profile</h1>
        <p className="text-slate-400 text-sm text-center mb-6">Choose a unique nickname to get started on Torn War Reporter.</p>
        
        <form onSubmit={handleSave} className="space-y-5">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Nickname</label>
            <input
              type="text"
              name="nickname"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="Enter nickname..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg text-white px-4 py-3 text-sm focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>
          
          {error && (
            <p className="error-message text-red-400 text-xs bg-red-400/10 py-2.5 px-3 rounded-lg border border-red-400/20 font-medium">
              {error}
            </p>
          )}
          
          <button
            type="submit"
            disabled={saving}
            className="w-full py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-lg transition-colors flex justify-center items-center gap-2 glowing-btn disabled:opacity-70 cursor-pointer"
          >
            {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Save Profile'}
          </button>
        </form>
      </div>
    </div>
  );
};

// ==================== PROFILE SETTINGS VIEW ====================
interface SettingsViewProps {
  user: any;
  setUser: (user: any) => void;
  navigateTo: (path: string) => void;
}

const SettingsView: React.FC<SettingsViewProps> = ({ user, setUser, navigateTo }) => {
  const [nickname, setNickname] = useState(user?.nickname || '');
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    if (user) {
      setNickname(user.nickname || '');
    }
  }, [user]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('FRONTEND: handleUpdate called with nickname:', nickname);
    if (!nickname.trim()) {
      setError('Nickname is required');
      return;
    }
    setUpdating(true);
    setError('');
    setSuccess('');
    try {
      const response = await axios.post('/api/profile/update', { nickname });
      console.log('FRONTEND: handleUpdate response:', response.data);
      if (response.data.status === 'success') {
        setUser(response.data.profile);
        setSuccess('Profile updated successfully!');
      }
    } catch (err: any) {
      console.error('FRONTEND: handleUpdate error:', err.response?.data || err.message);
      setError(err.response?.data?.error || 'Failed to update profile');
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b1120] text-slate-300 font-sans p-6 selection:bg-cyan-500/30">
      <div className="max-w-xl mx-auto space-y-6">
        <header className="flex items-center gap-4 border-b border-slate-800 pb-4">
          <button onClick={() => navigateTo('/')} className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors cursor-pointer">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Profile Settings</h1>
            <p className="text-slate-500 text-xs mt-0.5">Manage your public identity and profile media</p>
          </div>
        </header>

        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur-sm space-y-6">
          {/* Identity Info */}
          <div className="flex items-center gap-4 pb-6 border-b border-slate-800/60">
            <div className="w-16 h-16 rounded-full bg-cyan-900/30 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-2xl">
              {user?.nickname ? user.nickname.substring(0, 2).toUpperCase() : '??'}
            </div>
            <div>
              <div className="text-xs text-slate-500 font-bold uppercase tracking-wider">Public Handle</div>
              <div className="profile-display-name text-xl font-bold text-white mt-0.5">{user?.nickname}</div>
              {/* Real Name and Email are dead data, completely hidden from UI */}
              <div className="profile-real-name" style={{ display: 'none' }}>
                {user?.given_name} {user?.family_name} ({user?.email})
              </div>
            </div>
          </div>

          {/* Nickname Form */}
          <form onSubmit={handleUpdate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-2">Change Nickname</label>
              <input
                type="text"
                name="nickname"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg text-white px-3 py-2 text-sm focus:outline-none focus:border-cyan-500 transition-colors"
              />
              <p className="text-xs text-slate-500 mt-1.5">Note: Nickname changes are limited to once every 14 days after your initial change.</p>
            </div>

            {success && (
              <div className="success-message text-green-400 text-xs bg-green-400/10 py-2.5 px-3 rounded-lg border border-green-400/20 font-medium">
                {success}
              </div>
            )}

            {error && (
              <div className="error-message-inline text-red-400 text-xs bg-red-400/10 py-2.5 px-3 rounded-lg border border-red-400/20 font-medium">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={updating}
              className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-70 cursor-pointer"
            >
              {updating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Update Profile'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

// ==================== DASHBOARD VIEW ====================
interface DashboardViewProps {
  user: any;
  navigateTo: (path: string) => void;
}

const DashboardView: React.FC<DashboardViewProps> = ({ user, navigateTo }) => {
  const [warId, setWarId] = useState('');
  const [prizeTotal, setPrizeTotal] = useState('100000000');
  const [factionShare, setFactionShare] = useState('30');
  const [guaranteedShare, setGuaranteedShare] = useState('10');

  const [metric, setMetric] = useState('respect');
  const [useBonusRespect, setUseBonusRespect] = useState(true);

  const [enableAssist, setEnableAssist] = useState(true);
  const [assistBonus, setAssistBonus] = useState('1000000');

  const [enableDefend, setEnableDefend] = useState(true);
  const [defendBonus, setDefendBonus] = useState('500000');

  const [enablePenalty, setEnablePenalty] = useState(true);
  const [lossPenalty, setLossPenalty] = useState('250000');

  const [enableStalemate, setEnableStalemate] = useState(false);
  const [stalemateBonus, setStalemateBonus] = useState('100000');

  const [loading, setLoading] = useState(false);
  const [reportData, setReportData] = useState<any>(null);
  const [error, setError] = useState('');

  const generateReport = async () => {
    if (!warId) {
      setError('Please enter a valid War ID');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/generate', {
        war_id: warId,
        prize_total: prizeTotal,
        faction_share: factionShare,
        guaranteed_share: guaranteedShare,
        settings: {
          participation_metric: metric,
          use_bonus_respect: useBonusRespect ? 'true' : 'false',
          enable_assist_bonus: enableAssist ? 'true' : 'false',
          assist_bonus_value: assistBonus,
          enable_defend_bonus: enableDefend ? 'true' : 'false',
          defend_bonus_value: defendBonus,
          enable_hit_taken_penalty: enablePenalty ? 'true' : 'false',
          hit_taken_penalty_value: lossPenalty,
          enable_stalemate_bonus: enableStalemate ? 'true' : 'false',
          stalemate_bonus_value: stalemateBonus
        }
      });

      if (response.data.status === 'success') {
        setReportData(response.data.data);
      } else {
        setError(response.data.detail || 'An error occurred.');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b1120] text-slate-300 font-sans p-6 selection:bg-cyan-500/30">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <header className="flex justify-between items-end border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
              <Calculator className="text-cyan-400 w-8 h-8" />
              Torn War Reporter <span className="text-cyan-400 font-light text-2xl">v3 Web</span>
            </h1>
            <p className="text-slate-500 mt-1 text-sm">Dynamic Payout Dashboard & Report Generator</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigateTo('/settings/profile')}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors border border-slate-700 text-white cursor-pointer"
            >
              <User className="w-4 h-4" /> Profile Settings
            </button>
            <button
              disabled={!reportData}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors border border-slate-700 text-white cursor-pointer"
            >
              <Download className="w-4 h-4" /> Export HTML
            </button>
          </div>
        </header>

        {/* Welcome Panel */}
        <div className="bg-slate-900/30 border border-slate-800/80 rounded-xl p-4 flex justify-between items-center px-6">
          <span className="text-slate-400 text-sm font-medium">Logged in as <strong className="text-cyan-400 font-bold">{user?.nickname}</strong></span>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* Left Panel: Controls */}
          <div className="lg:col-span-4 flex flex-col gap-6">

            {/* Core Settings */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 shadow-xl backdrop-blur-sm">
              <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Settings className="w-4 h-4" /> Core Config
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">War ID</label>
                  <input type="text" value={warId} onChange={e => setWarId(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded text-white px-3 py-2 text-sm focus:outline-none focus:border-cyan-500 transition-colors" placeholder="e.g. 123456" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Prize Total ($)</label>
                  <input type="text" value={prizeTotal} onChange={e => setPrizeTotal(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded text-white px-3 py-2 text-sm focus:outline-none focus:border-cyan-500 transition-colors" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">Faction Share %</label>
                    <input type="text" value={factionShare} onChange={e => setFactionShare(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded text-white px-3 py-2 text-sm focus:outline-none focus:border-cyan-500" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">Guaranteed %</label>
                    <input type="text" value={guaranteedShare} onChange={e => setGuaranteedShare(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded text-white px-3 py-2 text-sm focus:outline-none focus:border-cyan-500" />
                  </div>
                </div>
              </div>
            </div>

            {/* Adjustments & Metrics */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 shadow-xl backdrop-blur-sm">
              <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" /> Mathematical Toggles
              </h2>

              <div className="space-y-5">

                {/* Metric Select */}
                <div className="space-y-2">
                  <div className="flex bg-slate-950 rounded-lg p-1 border border-slate-800">
                    <button onClick={() => setMetric('respect')} className={`flex-1 text-xs py-1.5 rounded-md transition-colors font-medium cursor-pointer ${metric === 'respect' ? 'bg-cyan-900/40 text-cyan-400' : 'text-slate-500 hover:text-slate-300'}`}>Respect Based</button>
                    <button onClick={() => setMetric('hits')} className={`flex-1 text-xs py-1.5 rounded-md transition-colors font-medium cursor-pointer ${metric === 'hits' ? 'bg-cyan-900/40 text-cyan-400' : 'text-slate-500 hover:text-slate-300'}`}>Hits Based</button>
                  </div>

                  {metric === 'respect' && (
                    <label className="flex items-center gap-2 cursor-pointer mt-2 pl-1">
                      <input type="checkbox" checked={useBonusRespect} onChange={e => setUseBonusRespect(e.target.checked)} className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500 focus:ring-offset-slate-900" />
                      <span className="text-xs text-slate-400 font-medium">Include Chain Multipliers (Total Respect)</span>
                    </label>
                  )}
                </div>

                <div className="h-px bg-slate-800 w-full" />

                {/* Toggles */}
                {[
                  { name: 'Assists Bonus', icon: Handshake, state: enableAssist, setter: setEnableAssist, val: assistBonus, valSet: setAssistBonus, color: 'text-green-400 bg-green-500/10' },
                  { name: 'Defends Bonus', icon: Shield, state: enableDefend, setter: setEnableDefend, val: defendBonus, valSet: setDefendBonus, color: 'text-emerald-400 bg-emerald-500/10' },
                  { name: 'Losses Penalty', icon: Target, state: enablePenalty, setter: setEnablePenalty, val: lossPenalty, valSet: setLossPenalty, color: 'text-red-400 bg-red-500/10' },
                  { name: 'Stalemate Bonus', icon: Shield, state: enableStalemate, setter: setEnableStalemate, val: stalemateBonus, valSet: setStalemateBonus, color: 'text-blue-400 bg-blue-500/10' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center justify-between gap-3">
                    <label className="flex items-center gap-3 cursor-pointer select-none">
                      <input type="checkbox" checked={item.state} onChange={e => item.setter(e.target.checked)} className="sr-only peer" />
                      <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-cyan-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500 relative transition-colors"></div>
                      <span className="text-sm font-medium text-slate-300 flex items-center gap-1.5"><item.icon className={`w-3.5 h-3.5 ${item.state ? item.color.split(' ')[0] : 'text-slate-500'}`} /> {item.name}</span>
                    </label>
                    <input
                      type="text"
                      value={item.val}
                      onChange={e => item.valSet(e.target.value)}
                      disabled={!item.state}
                      className="w-24 bg-slate-950 border border-slate-800 rounded text-right text-slate-300 px-2 py-1 text-xs outline-none focus:border-cyan-500 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
                    />
                  </div>
                ))}
              </div>

              <div className="mt-6">
                <button
                  onClick={generateReport}
                  disabled={loading}
                  className="w-full py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-lg transition-colors flex justify-center items-center gap-2 glowing-btn disabled:opacity-70 disabled:cursor-not-allowed cursor-pointer"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Calculate Payouts'}
                </button>
                {error && <p className="text-red-400 text-xs mt-3 text-center bg-red-400/10 py-2 rounded border border-red-400/20">{error}</p>}
              </div>

            </div>
          </div>

          {/* Right Panel: Results */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            <AnimatePresence mode="wait">
              {reportData ? (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  className="space-y-6"
                >
                  {/* Summary Cards */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                      <p className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">Prize Pool</p>
                      <p className="text-3xl font-light text-white">{formatMoney(Number(prizeTotal))}</p>
                    </div>
                    <div className="bg-slate-900/50 border border-cyan-500/20 p-5 rounded-xl relative overflow-hidden group">
                      <div className="absolute inset-0 bg-cyan-500/5 translate-y-full group-hover:translate-y-0 transition-transform duration-300 rounded-xl" />
                      <p className="text-cyan-500/70 text-xs font-bold uppercase tracking-wider mb-1 relative z-10">Faction Keep</p>
                      <p className="text-3xl font-bold text-cyan-400 relative z-10">{formatMoney(Number(prizeTotal) * (Number(factionShare) / 100))}</p>
                    </div>
                    <div className="bg-slate-900/50 border border-green-500/20 p-5 rounded-xl relative overflow-hidden group">
                      <div className="absolute inset-0 bg-green-500/5 translate-y-full group-hover:translate-y-0 transition-transform duration-300 rounded-xl" />
                      <p className="text-green-500/70 text-xs font-bold uppercase tracking-wider mb-1 relative z-10">Member Pool</p>
                      <p className="text-3xl font-bold text-emerald-400 relative z-10">{formatMoney(Number(prizeTotal) - (Number(prizeTotal) * (Number(factionShare) / 100)))}</p>
                    </div>
                  </div>

                  {/* Table */}
                  <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
                    <div className="px-5 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/80">
                      <h3 className="font-bold text-white tracking-wide">Participation Payouts</h3>
                      <span className="text-xs font-medium bg-slate-800 text-slate-300 px-3 py-1 rounded-full">{reportData.member_stats.length} Active Members</span>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-slate-950/50 text-slate-400 border-b border-slate-800">
                          <tr>
                            <th className="px-5 py-3 font-medium">Member</th>
                            <th className="px-5 py-3 font-medium text-right">Metric ({metric})</th>
                            <th className="px-5 py-3 font-medium text-right">Adjustments</th>
                            <th className="px-5 py-3 font-medium text-right">Base Payout</th>
                            <th className="px-5 py-3 font-bold text-white text-right">Final Output</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {reportData.member_stats.map(([id, stats]: [string, any]) => (
                            <tr key={id} className="hover:bg-slate-800/20 transition-colors">
                              <td className="px-5 py-4">
                                <div className="font-bold text-cyan-400">{stats.name}</div>
                                <div className="text-[10px] text-slate-500 font-mono mt-0.5">[{id}]</div>
                              </td>
                              <td className="px-5 py-4 text-right">
                                <div className="text-slate-200">{metric === 'hits' ? stats.hits_made : stats.respect_gained.toFixed(2)}</div>
                                <div className="text-[10px] text-slate-500 mt-0.5">Share: {((stats.participation_payout / (Number(prizeTotal) - (Number(prizeTotal) * (Number(factionShare) / 100)))) * 100 || 0).toFixed(2)}%</div>
                              </td>
                              <td className="px-5 py-4 text-right font-mono">
                                <span className={stats.adjustments > 0 ? 'text-green-400' : stats.adjustments < 0 ? 'text-red-400' : 'text-slate-600'}>
                                  {stats.adjustments > 0 ? '+' : ''}{formatMoney(stats.adjustments)}
                                </span>
                              </td>
                              <td className="px-5 py-4 text-right text-slate-400 font-mono">
                                {formatMoney(stats.respect_payout)}
                              </td>
                              <td className="px-5 py-4 text-right font-bold text-white font-mono bg-cyan-950/10">
                                {formatMoney(stats.final_payout)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                </motion.div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-600 min-h-[500px] border-2 border-dashed border-slate-800 rounded-xl bg-slate-900/20">
                  <Calculator className="w-16 h-16 mb-4 opacity-50 text-slate-500" />
                  <p className="text-lg font-medium">No Data Calculated</p>
                  <p className="text-sm mt-1 max-w-sm text-center opacity-70">Enter your Torn War ID and click "Calculate Payouts" to fetch data and process the report.</p>
                </div>
              )}
            </AnimatePresence>
          </div>

        </div>
      </div>
    </div>
  );
};

// ==================== MAIN APP ====================
function App() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const [user, setUser] = useState<any>(null);
  const [loadingUser, setLoadingUser] = useState(true);

  // Router navigation helper
  const navigateTo = (path: string) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
  };

  // Sync with browser history back/forward
  useEffect(() => {
    const handleLocationChange = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener('popstate', handleLocationChange);
    return () => window.removeEventListener('popstate', handleLocationChange);
  }, []);

  // Fetch current user profile
  const fetchProfile = async () => {
    try {
      const res = await axios.get('/api/profile');
      setUser(res.data);
      if (!res.data.nickname) {
        if (window.location.pathname !== '/onboarding') {
          navigateTo('/onboarding');
        }
      } else {
        if (window.location.pathname === '/login' || window.location.pathname === '/onboarding') {
          navigateTo('/');
        }
      }
    } catch (err) {
      setUser(null);
      if (window.location.pathname !== '/login') {
        navigateTo('/login');
      }
    } finally {
      setLoadingUser(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, [currentPath]);

  if (loadingUser) {
    return (
      <div className="min-h-screen bg-[#0b1120] flex items-center justify-center text-cyan-400">
        <Loader2 className="w-10 h-10 animate-spin" />
      </div>
    );
  }

  // Render view based on route
  if (currentPath === '/login') {
    return <LoginView setUser={setUser} navigateTo={navigateTo} />;
  } else if (currentPath === '/onboarding') {
    return <OnboardingView setUser={setUser} navigateTo={navigateTo} />;
  } else if (currentPath === '/settings/profile') {
    return <SettingsView user={user} setUser={setUser} navigateTo={navigateTo} />;
  } else {
    return <DashboardView user={user} navigateTo={navigateTo} />;
  }
}

export default App;
