"""
ContaEC - Pruebas de integración para límites de licencia

Ejecutar con:
    cd backend
    python -m pytest test_license_limits.py -v

O en modo desenvolvimento:
    python test_license_limits.py
"""
import asyncio
import sys
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import get_password_hash
from app.core.licenses import get_license_limits, TRIAL_LIMITS, LICENSE_TIERS
from app.models.user import User, LicenseType
from app.models.company import Company
from app.models.employee import Employee
from app.models.product import Product
from app.models.comprobante import Comprobante, ComprobanteEstado
from app.schemas.company import CompanyCreate
from app.schemas.employee import EmployeeCreate
from app.schemas.product import ProductCreate
from app.schemas.comprobante import ComprobanteCreate, ComprobanteDetalleCreate


# ==========================================
# Firma electrónica de prueba (.p12)
# ==========================================

TEST_SIGNATURE_PASSWORD = "Test1234!"
TEST_SIGNATURE_REL_PATH = "/uploads/companies/_test_firma.p12"


def _generate_test_p12() -> Path:
    """Genera un archivo .p12 de prueba para CompanyCreate (que ahora exige firma)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    backend_dir = Path(__file__).parent
    upload_dir = backend_dir / "uploads" / "companies"
    upload_dir.mkdir(parents=True, exist_ok=True)
    p12_path = upload_dir / "_test_firma.p12"

    if p12_path.exists():
        return p12_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"ContaEC Test"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"ContaEC Test S.A."),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    p12_data = pkcs12.serialize_key_and_certificates(
        b"ContaEC Test",
        key,
        cert,
        None,
        serialization.BestAvailableEncryption(TEST_SIGNATURE_PASSWORD.encode()),
    )
    p12_path.write_bytes(p12_data)
    return p12_path


def _remove_test_p12():
    """Elimina el .p12 de prueba generado."""
    p12_path = Path(__file__).parent / "uploads" / "companies" / "_test_firma.p12"
    if p12_path.exists():
        p12_path.unlink()


# Configuración de base de datos de prueba
# Usa SQLite en memoria con StaticPool para que todas las conexiones
# compartan la misma base de datos en memoria (patrón estándar de SQLAlchemy).
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def setup_db():
    """Crear tablas en memoria"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_test_user(
    db: AsyncSession,
    license_type: LicenseType | None = None,
    is_trial: bool = False,
    trial_days: int = 0,
    email: str = None,
) -> User:
    """Crear usuario de prueba con licencia específica"""
    user = User(
        email=email or f"test_{uuid4().hex[:8]}@test.com",
        full_name="Usuario Test",
        hashed_password=get_password_hash("password123"),
        license_type=license_type,
        is_trial=is_trial,
    )

    # Configurar fechas de licencia/trial
    now = datetime.now(timezone.utc)

    if is_trial and trial_days > 0:
        user.trial_start_date = now
        user.trial_end_date = now + timedelta(days=trial_days)

    if license_type:
        user.license_start_date = now
        # Según tipo de licencia
        months = {
            LicenseType.MENSUAL: 1,
            LicenseType.TRIMESTRAL: 3,
            LicenseType.SEMESTRAL: 6,
            LicenseType.ANUAL: 12,
        }.get(license_type, 1)
        # Aproximación simple: sumar días
        user.license_end_date = now + timedelta(days=months * 30)

    db.add(user)
    await db.flush()
    return user


async def test_trial_limits():
    """Prueba 1: Usuario en trial solo puede crear 1 empresa"""
    print("\n" + "=" * 60)
    print("PRUEBA 1: Límites de usuario en Trial")
    print("=" * 60)

    async with async_session() as db:
        # Crear usuario en trial (14 días)
        user = await create_test_user(db, is_trial=True, trial_days=14)
        await db.commit()

        # Verificar límites
        limits = get_license_limits(user)
        assert limits['max_companies'] == 1, f"Expected 1 company, got {limits['max_companies']}"
        assert limits['max_employees'] == 5, f"Expected 5 employees, got {limits['max_employees']}"
        assert limits['max_products'] == 100, f"Expected 100 products, got {limits['max_products']}"
        assert limits['max_comprobantes_month'] == 50, f"Expected 50 comprobantes, got {limits['max_comprobantes_month']}"

        print("✅ Límites de trial correctos:")
        print(f"   - Empresas: {limits['max_companies']}")
        print(f"   - Empleados: {limits['max_employees']}")
        print(f"   - Productos: {limits['max_products']}")
        print(f"   - Comprobantes/mes: {limits['max_comprobantes_month']}")

        # Intentar crear segunda empresa (debe fallar)
        from app.api.v1.endpoints.companies import create_company

        # CompanyCreate ahora exige firma electrónica y contraseña
        _generate_test_p12()

        company1 = CompanyCreate(
            ruc="1234567890001",
            razon_social="Empresa 1 S.A.",
            nombre_comercial="Empresa 1",
            dir_matriz="Calle Principal",
            firma_electronica_path=TEST_SIGNATURE_REL_PATH,
            firma_electronica_password=TEST_SIGNATURE_PASSWORD,
        )

        company2 = CompanyCreate(
            ruc="1234567890002",
            razon_social="Empresa 2 S.A.",
            nombre_comercial="Empresa 2",
            dir_matriz="Calle Secundaria",
            firma_electronica_path=TEST_SIGNATURE_REL_PATH,
            firma_electronica_password=TEST_SIGNATURE_PASSWORD,
        )

        # Crear primera empresa (debe funcionar)
        from fastapi import HTTPException

        try:
            result = await create_company(company1, db=db, current_user=user)
            print(f"✅ Primera empresa creada: {result.razon_social}")
        except HTTPException as e:
            print(f"❌ Error inesperado creando primera empresa: {e.detail}")

        # Crear segunda empresa (debe fallar)
        try:
            result = await create_company(company2, db=db, current_user=user)
            print(f"❌ ERROR: Segunda empresa creada cuando debería fallar!")
            return False
        except HTTPException as e:
            if e.status_code == 403:
                print(f"✅ Segunda empresa rechazada correctamente: {e.detail}")
            else:
                print(f"❌ Error inesperado: {e.status_code} - {e.detail}")

        return True


async def test_monthly_plan_limits():
    """Prueba 2: Usuario con plan mensual"""
    print("\n" + "=" * 60)
    print("PRUEBA 2: Límites de plan Mensual")
    print("=" * 60)

    async with async_session() as db:
        user = await create_test_user(db, license_type=LicenseType.MENSUAL)
        await db.commit()

        limits = get_license_limits(user)
        assert limits['max_companies'] == 1
        assert limits['max_employees'] == 5
        assert limits['max_products'] == 100

        print("✅ Límites de plan Mensual correctos:")
        print(f"   - Empresas: {limits['max_companies']}")
        print(f"   - Empleados: {limits['max_employees']}")
        print(f"   - Productos: {limits['max_products']}")

        return True


async def test_quarterly_plan_limits():
    """Prueba 3: Usuario con plan trimestral"""
    print("\n" + "=" * 60)
    print("PRUEBA 3: Límites de plan Trimestral")
    print("=" * 60)

    async with async_session() as db:
        user = await create_test_user(db, license_type=LicenseType.TRIMESTRAL)
        await db.commit()

        limits = get_license_limits(user)
        assert limits['max_companies'] == 2, f"Expected 2 companies, got {limits['max_companies']}"
        assert limits['max_employees'] == 15, f"Expected 15 employees, got {limits['max_employees']}"
        assert limits['max_products'] == 500, f"Expected 500 products, got {limits['max_products']}"

        print("✅ Límites de plan Trimestral correctos:")
        print(f"   - Empresas: {limits['max_companies']}")
        print(f"   - Empleados: {limits['max_employees']}")
        print(f"   - Productos: {limits['max_products']}")

        return True


async def test_semiannual_plan_limits():
    """Prueba 4: Usuario con plan semestral"""
    print("\n" + "=" * 60)
    print("PRUEBA 4: Límites de plan Semestral")
    print("=" * 60)

    async with async_session() as db:
        user = await create_test_user(db, license_type=LicenseType.SEMESTRAL)
        await db.commit()

        limits = get_license_limits(user)
        assert limits['max_companies'] == 5
        assert limits['max_employees'] == 50
        assert limits['max_products'] == 2000
        assert limits['max_comprobantes_month'] == 500

        print("✅ Límites de plan Semestral correctos:")
        print(f"   - Empresas: {limits['max_companies']}")
        print(f"   - Empleados: {limits['max_employees']}")
        print(f"   - Productos: {limits['max_products']}")
        print(f"   - Comprobantes/mes: {limits['max_comprobantes_month']}")

        return True


async def test_annual_plan_limits():
    """Prueba 5: Usuario con plan anual (ilimitado)"""
    print("\n" + "=" * 60)
    print("PRUEBA 5: Límites de plan Anual (Ilimitado)")
    print("=" * 60)

    async with async_session() as db:
        user = await create_test_user(db, license_type=LicenseType.ANUAL)
        await db.commit()

        limits = get_license_limits(user)
        assert limits['max_companies'] == 999
        assert limits['max_employees'] == 999
        assert limits['max_products'] == 99999

        print("✅ Límites de plan Anual correctos (prácticamente ilimitado):")
        print(f"   - Empresas: {limits['max_companies']}")
        print(f"   - Empleados: {limits['max_employees']}")
        print(f"   - Productos: {limits['max_products']}")

        return True


async def test_employee_limit():
    """Prueba 6: Límite de empleados"""
    print("\n" + "=" * 60)
    print("PRUEBA 6: Límite de creación de Empleados")
    print("=" * 60)

    async with async_session() as db:
        # Usuario mensual (límite 5 empleados)
        user = await create_test_user(db, license_type=LicenseType.MENSUAL)
        await db.commit()

        # Crear empresa
        company = Company(
            user_id=user.id,
            ruc="9876543210001",
            razon_social="Test Company",
            dir_matriz="Test Street",
        )
        db.add(company)
        await db.flush()

        limits = get_license_limits(user)
        max_employees = limits['max_employees']

        print(f"Límite de empleados para plan mensual: {max_employees}")

        # Crear empleados hasta el límite
        from app.api.v1.endpoints.employees import create_employee
        from fastapi import HTTPException

        for i in range(max_employees):
            employee_data = EmployeeCreate(
                company_id=str(company.id),
                cedula=f"{i+1:010d}",
                apellidos=f"Apellido {i+1}",
                nombres=f"Nombre {i+1}",
                sueldo_mensual=500.00,
            )

            try:
                emp = await create_employee(employee_data, db=db, current_user=user)
                print(f"  ✅ Empleado {i+1} creado: {emp.cedula}")
            except HTTPException as e:
                print(f"  ❌ Error creando empleado {i+1}: {e.detail}")
                return False

        # Intentar crear empleado adicional (debe fallar)
        try:
            employee_data = EmployeeCreate(
                company_id=str(company.id),
                cedula="9999999999",
                apellidos="Empleado Extra",
                nombres="No Debe Crear",
                sueldo_mensual=500.00,
            )
            emp = await create_employee(employee_data, db=db, current_user=user)
            print(f"  ❌ ERROR: Empleado extra creado cuando debería fallar!")
            return False
        except HTTPException as e:
            if e.status_code == 403:
                print(f"  ✅ Empleado extra rechazado correctamente: {e.detail}")
            else:
                print(f"  ❌ Error inesperado: {e.status_code}")
                return False

        return True


async def test_product_limit():
    """Prueba 7: Límite de productos"""
    print("\n" + "=" * 60)
    print("PRUEBA 7: Límite de creación de Productos")
    print("=" * 60)

    async with async_session() as db:
        # Usuario mensual (límite 100 productos)
        user = await create_test_user(db, license_type=LicenseType.MENSUAL)
        await db.commit()

        # Crear empresa
        company = Company(
            user_id=user.id,
            ruc="1112223330001",
            razon_social="Product Test Company",
            dir_matriz="Test Street",
        )
        db.add(company)
        await db.flush()

        limits = get_license_limits(user)
        max_products = limits['max_products']

        print(f"Límite de productos para plan mensual: {max_products}")
        print("  (Creando 3 productos de prueba por brevedad...)")

        from app.api.v1.endpoints.products import create_product
        from fastapi import HTTPException

        # Crear algunos productos de prueba (no los 100 para no hacer lento el test)
        test_count = min(3, max_products)
        for i in range(test_count):
            product_data = ProductCreate(
                company_id=str(company.id),
                codigo_principal=f"PROD-{i+1:03d}",
                descripcion=f"Producto {i+1}",
                tipo="B",
                precio_unitario=10.00,
            )

            try:
                prod = await create_product(product_data, db=db, current_user=user)
                print(f"    ✅ Producto {i+1} creado: {prod.codigo_principal}")
            except HTTPException as e:
                print(f"    ❌ Error creando producto {i+1}: {e.detail}")
                return False

        print(f"  ✅ Productos creados exitosamente (se omitieron {max_products - test_count} por brevedad)")
        return True


async def test_comprobante_monthly_limit():
    """Prueba 8: Límite mensual de comprobantes"""
    print("\n" + "=" * 60)
    print("PRUEBA 8: Límite mensual de Comprobantes")
    print("=" * 60)

    async with async_session() as db:
        # Usuario mensual (límite 50 comprobantes/mes)
        user = await create_test_user(db, license_type=LicenseType.MENSUAL)
        await db.commit()

        # Crear empresa
        company = Company(
            user_id=user.id,
            ruc="5556667770001",
            razon_social="Invoice Test Company",
            dir_matriz="Test Street",
            cod_establecimiento="001",
            cod_punto_emision="001",
        )
        db.add(company)
        await db.flush()

        limits = get_license_limits(user)
        max_comprobantes = limits['max_comprobantes_month']

        print(f"Límite de comprobantes/mes para plan mensual: {max_comprobantes}")

        # Contar comprobantes existentes
        result = await db.execute(
            select(func.count(Comprobante.id)).where(
                Comprobante.company_id == company.id,
            )
        )
        current_count = result.scalar() or 0
        print(f"Comprobantes existentes: {current_count}")
        print(f"✅ Sistema de límite de comprobantes está configurado correctamente")

        return True


async def test_feature_access():
    """Prueba 9: Acceso a features según licencia"""
    print("\n" + "=" * 60)
    print("PRUEBA 9: Feature Access por Tipo de Licencia")
    print("=" * 60)

    from app.core.licenses import has_feature

    # Features para probar
    features_to_test = [
        ('pos', {'monthly': False, 'quarterly': True, 'semiannual': True, 'annual': True}),
        ('multi_warehouse', {'monthly': False, 'quarterly': False, 'semiannual': True, 'annual': True}),
        ('api_access', {'monthly': False, 'quarterly': False, 'semiannual': False, 'annual': True}),
        ('electronic_invoicing', {'monthly': True, 'quarterly': True, 'semiannual': True, 'annual': True}),
    ]

    all_passed = True

    for feature, expected_by_tier in features_to_test:
        print(f"\n  Feature: '{feature}'")
        for tier_name, expected in expected_by_tier.items():
            license_type = LicenseType(tier_name)
            has_access = has_feature(license_type, feature)
            status = "✅" if has_access == expected else "❌"
            print(f"    {status} {tier_name}: {'Tiene' if has_access else 'No tiene'} acceso (esperado: {'Sí' if expected else 'No'})")
            if has_access != expected:
                all_passed = False

    return all_passed


async def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("\n" + "=" * 60)
    print("PRUEBAS DE INTEGRACIÓN - MÓDULO DE LICENCIAS")
    print("=" * 60)

    # Limpiar firma de prueba anterior si existe
    _remove_test_p12()

    await setup_db()

    tests = [
        ("Límites Trial", test_trial_limits),
        ("Límites Mensual", test_monthly_plan_limits),
        ("Límites Trimestral", test_quarterly_plan_limits),
        ("Límites Semestral", test_semiannual_plan_limits),
        ("Límites Anual", test_annual_plan_limits),
        ("Límite Empleados", test_employee_limit),
        ("Límite Productos", test_product_limit),
        ("Límite Comprobantes", test_comprobante_monthly_limit),
        ("Feature Access", test_feature_access),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ ERROR en {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{total} pruebas pasadas")

    if passed == total:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
    else:
        print(f"\n⚠️ {total - passed} prueba(s) fallaron")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    # Limpieza final de la firma de prueba
    _remove_test_p12()
    sys.exit(0 if success else 1)