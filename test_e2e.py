#!/usr/bin/env python3
import sys
import json
import httpx

BASE_URL = "http://localhost:8000"

def test_login():
    print("=" * 60)
    print("测试 1: 用户登录")
    print("=" * 60)
    try:
        response = httpx.post(
            f"{BASE_URL}/api/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"✅ 登录成功，token: {token[:30]}...")
            return token
        else:
            print(f"❌ 登录失败: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return None

def test_create_simulation(token):
    print("\n" + "=" * 60)
    print("测试 2: 创建模拟任务")
    print("=" * 60)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        sim_data = {
            "name": "端到端测试模拟",
            "description": "E2E测试用例",
            "core_radius": 3.48e6,
            "inner_core_radius": 1.22e6,
            "viscosity": 1.0e-2,
            "thermal_expansion": 1.0e-5,
            "icb_heat_flux": 0.05,
            "cmb_heat_flux": 0.01,
            "dipole_moment": 8.0e22,
            "rayleigh_number": 1.0e8,
            "prandtl_number": 1.0,
            "magnetic_prandtl_number": 2.0,
            "ekman_number": 1.0e-8,
            "n_radial": 16,
            "n_theta": 32,
            "n_phi": 64,
            "max_iterations": 100
        }
        response = httpx.post(
            f"{BASE_URL}/api/simulations/",
            headers=headers,
            json=sim_data
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            sim_id = data.get("id")
            print(f"✅ 创建成功，任务ID: {sim_id}")
            print(f"  任务名称: {data.get('name')}")
            print(f"  状态: {data.get('status')}")
            return sim_id
        else:
            print(f"❌ 创建失败: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建异常: {e}")
        return None

def test_get_simulation_list(token):
    print("\n" + "=" * 60)
    print("测试 3: 获取任务列表")
    print("=" * 60)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = httpx.get(
            f"{BASE_URL}/api/simulations/",
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 获取成功，共 {len(data)} 个任务")
            for i, sim in enumerate(data[:3]):
                print(f"  [{i+1}] {sim.get('name')} - {sim.get('status')}")
            return True
        else:
            print(f"❌ 获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 获取异常: {e}")
        return False

def test_generate_pdf(token, sim_id):
    print("\n" + "=" * 60)
    print("测试 4: 生成PDF报告")
    print("=" * 60)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = httpx.post(
            f"{BASE_URL}/api/reports/{sim_id}/generate",
            headers=headers,
            timeout=60.0
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ PDF生成成功")
            print(f"  报告路径: {data.get('report_path')}")
            print(f"  报告大小: {data.get('report_size')} bytes")
            return True
        else:
            print(f"❌ PDF生成失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ PDF生成异常: {e}")
        return False

def test_generate_animation(token, sim_id):
    print("\n" + "=" * 60)
    print("测试 5: 生成动画")
    print("=" * 60)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = httpx.post(
            f"{BASE_URL}/api/reports/{sim_id}/animation",
            headers=headers,
            params={"animation_type": "magnetic_field"},
            timeout=120.0
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 动画生成成功")
            print(f"  动画路径: {data.get('animation_path')}")
            print(f"  动画大小: {data.get('file_size')} bytes")
            print(f"  动画格式: {data.get('format')}")
            return True
        else:
            print(f"❌ 动画生成失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 动画生成异常: {e}")
        return False

def test_recommendation(token, sim_id):
    print("\n" + "=" * 60)
    print("测试 6: 智能推荐")
    print("=" * 60)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = httpx.post(
            f"{BASE_URL}/api/reports/{sim_id}/recommend",
            headers=headers,
            json={
                "target_dipole_moment": 8.5e22,
                "target_reversal_frequency": 0.3,
                "paleomagnetic_age_ma": 100.0
            },
            timeout=30.0
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 推荐成功")
            print(f"  推荐引擎: {data.get('engine_type')}")
            print(f"  推荐粘性: {data.get('recommended_viscosity'):.2e} m²/s")
            print(f"  推荐内核半径: {data.get('recommended_ic_radius'):.2e} m")
            print(f"  推荐生长速率: {data.get('recommended_growth_rate'):.2e} m/yr")
            print(f"  匹配度: {data.get('match_score'):.2%}")
            return True
        else:
            print(f"❌ 推荐失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 推荐异常: {e}")
        return False

def test_feature_importance(token):
    print("\n" + "=" * 60)
    print("测试 7: 特征重要性分析")
    print("=" * 60)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = httpx.get(
            f"{BASE_URL}/api/reports/feature-importance",
            headers=headers,
            timeout=30.0
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 特征重要性分析成功")
            print(f"  总特征数: {data.get('total_features')}")
            print(f"  Top 5 重要特征:")
            for i, feat in enumerate(data.get('top_features', [])[:5]):
                print(f"    {i+1}. {feat['feature']}: {feat['importance']:.4f}")
            return True
        else:
            print(f"❌ 特征重要性失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 特征重要性异常: {e}")
        return False

def main():
    print("\n" + "🚀" * 30)
    print("地核多物理场耦合模拟平台 - 端到端测试")
    print("🚀" * 30)
    
    token = test_login()
    if not token:
        print("\n❌ 登录失败，终止测试")
        sys.exit(1)
    
    sim_id = test_create_simulation(token)
    if not sim_id:
        print("\n❌ 创建模拟失败，终止测试")
        sys.exit(1)
    
    test_get_simulation_list(token)
    test_generate_pdf(token, sim_id)
    test_generate_animation(token, sim_id)
    test_recommendation(token, sim_id)
    test_feature_importance(token)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
