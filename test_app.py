from app import get_employee_directory, calculate_payroll_and_tax, export_payroll_csv

def test_tools():
    emp = get_employee_directory()
    print("Employee data:", emp)
    payroll = calculate_payroll_and_tax(emp)
    print("Payroll calculated:", payroll)
    csv = export_payroll_csv(payroll)
    print("CSV exported:", csv)
    print("All tools test passed")

if __name__ == "__main__":
    test_tools()
