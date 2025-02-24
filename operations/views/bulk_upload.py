# import pandas as pd
# from django.shortcuts import render, redirect
# from django.core.files.storage import FileSystemStorage
# from django.contrib import messages
# from django.core.mail import send_mail
# from django.db import IntegrityError
# from operations.models import ContributionRecord
# from accounts.models import CustomUser
# from datetime import datetime

# def bulk_upload_contributions(request):
#     if request.method == 'POST' and request.FILES.get('file'):
#         file = request.FILES['file']
#         fs = FileSystemStorage()
#         filename = fs.save(file.name, file)
#         file_url = fs.path(filename)

#         try:
#             df = pd.read_excel(file_url)
            
#             if not {'Email', 'Amount', 'Month', 'Year'}.issubset(df.columns):
#                 messages.error(request, "Invalid file format. Columns should be Email, Amount, Month, Year.")
#                 return redirect('upload_contributions')

#             preview_data = df.to_dict(orient='records')
#             request.session['contributions_preview'] = preview_data  # Store for final submission
#             return render(request, 'operations/contributions/preview_contributions.html', {'preview_data': preview_data})
        
#         except Exception as e:
#             messages.error(request, f"Error processing file: {e}")
#             return redirect('upload_contributions')
    
#     return render(request, 'operations/contributions/upload_contributions.html')

# def confirm_bulk_upload(request):
#     month_mapping = {
#             'january': 1, 'february': 2, 'march': 3, 'april': 4,
#             'may': 5, 'june': 6, 'july': 7, 'august': 8,
#             'september': 9, 'october': 10, 'november': 11, 'december': 12
#         }
#     preview_data = request.session.get('contributions_preview', [])
#     if not preview_data:
#         messages.error(request, "No data to process.")
#         return redirect('upload_contributions')

#     success_count, duplicate_count = 0, 0
#     current_year, current_month = datetime.now().year, datetime.now().month
    
#     for row in preview_data:
#         email, amount, month, year = row.get('Email'), row.get('Amount'), row.get('Month'), row.get('Year')
#         user = CustomUser.objects.filter(email=email).first()
#         # Mapping of month names to their integer values
        

#         # Convert month to lowercase and get its corresponding integer value
#         month = month_mapping.get(month.lower(), None)  # Default to None if not found

#         if user:
#             if ContributionRecord.objects.filter(employee=user, month=month, year=year).exists():
#                 duplicate_count += 1
#                 continue

#             try:
#                 ContributionRecord.objects.create(
#                     employee=user,
#                     amount=amount,
#                     month=month,
#                     year=year,
#                     status='paid'
#                 )
#                 success_count += 1
#             except IntegrityError:
#                 duplicate_count += 1

#     messages.success(request, f"Successfully uploaded {success_count} records. Skipped {duplicate_count} duplicates.")
#     del request.session['contributions_preview']
#     return redirect('upload_contributions')
import pandas as pd
import json
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.contrib import messages
from django.db import IntegrityError
from operations.models import ContributionRecord
from accounts.models import CustomUser
from datetime import datetime

def bulk_upload_contributions(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_url = fs.path(filename)

        try:
            df = pd.read_excel(file_url)

            if not {'Email', 'Amount', 'Month', 'Year'}.issubset(df.columns):
                return JsonResponse({"error": "Invalid file format. Columns should be Email, Amount, Month, Year."}, status=400)

            preview_data = df.to_dict(orient='records')
            request.session['contributions_preview'] = preview_data  # Store for final submission
            return JsonResponse({"success": True, "preview_data": preview_data})  # Send JSON response
        
        except Exception as e:
            return JsonResponse({"error": f"Error processing file: {str(e)}"}, status=500)

    return render(request, 'operations/contributions/upload_contributions.html')

def confirm_bulk_upload(request):
    month_mapping = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    preview_data = request.session.get('contributions_preview', [])
    if not preview_data:
        return JsonResponse({"error": "No data to process."}, status=400)

    success_count, duplicate_count = 0, 0

    for row in preview_data:
        email, amount, month, year = row.get('Email'), row.get('Amount'), row.get('Month'), row.get('Year')
        user = CustomUser.objects.filter(email=email).first()
        
        month = month_mapping.get(month.lower(), None)  # Convert month to number

        if user:
            if ContributionRecord.objects.filter(employee=user, month=month, year=year).exists():
                duplicate_count += 1
                continue

            try:
                ContributionRecord.objects.create(
                    employee=user,
                    amount=amount,
                    month=month,
                    year=year,
                    status='paid'
                )
                success_count += 1
            except IntegrityError:
                duplicate_count += 1

    del request.session['contributions_preview']
    return JsonResponse({"success": True, "uploaded": success_count, "duplicates": duplicate_count})
