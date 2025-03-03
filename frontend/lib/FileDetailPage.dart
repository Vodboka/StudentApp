import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:flutter_pdfview/flutter_pdfview.dart';
import 'LessonPage.dart';

class FileDetailPage extends StatefulWidget {
  final String fileName;

  FileDetailPage({required this.fileName});

  @override
  _FileDetailPageState createState() => _FileDetailPageState();
}

class _FileDetailPageState extends State<FileDetailPage> {
  String? pdfPath;
  String extractedText = "Loading text...";

  @override
  void initState() {
    super.initState();
    fetchFile();
    fetchExtractedText();
  }

  Future<void> fetchFile() async {
    final response = await http.get(
      Uri.parse("http://10.0.2.2:5000/get_file?file=${widget.fileName}"),
    );

    if (response.statusCode == 200) {
      final directory = await getApplicationDocumentsDirectory();
      final filePath = "${directory.path}/${widget.fileName}";
      final file = File(filePath);
      await file.writeAsBytes(response.bodyBytes);

      print("✅ PDF saved at: $filePath"); // Debugging output
      print("File exists: ${file.existsSync()}"); // Check if file exists

      setState(() {
        pdfPath = filePath;
      });
    } else {
      print("❌ Failed to fetch PDF");
    }
  }

  Future<void> fetchExtractedText() async {
    final response = await http.get(
      Uri.parse("http://10.0.2.2:5000/get_file_content?file=${widget.fileName}"),
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      setState(() {
        extractedText = data['extracted_text'] ?? "No extracted text available";
      });
    } else {
      print("❌ Failed to fetch extracted text");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.fileName)),
      body: pdfPath == null
          ? Center(child: CircularProgressIndicator())
          : PDFView(
              filePath: pdfPath!,
              enableSwipe: true,
              swipeHorizontal: true,
              autoSpacing: true,
              pageFling: true,
            ), // Show the PDF

      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => LessonPage(testText: extractedText), // Pass extracted text
            ),
          );
        },
        child: Icon(Icons.add), // "+" icon
        backgroundColor: Colors.deepOrange,
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.endFloat, // Bottom right
    );
  }
}
